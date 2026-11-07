"""API JSON cho các popup/nút trên giao diện. Mọi lỗi nghiệp vụ trả {ok: False, error: <mã>, message: <tiếng Việt>}."""
import json
import logging
from datetime import timedelta

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from forecast.models import (InventoryCount, Notification, PrepLine, PrepPlan, Role, Store, SystemConfig)
from forecast.permissions import api_role_required
from forecast.services import engine, insights, plans
from forecast.services.notifications import visible_for
from forecast.services.units import unit_for
from forecast.views import parse_date

MANAGER, STAFF, ADMIN = Role.MANAGER, Role.STAFF, Role.ADMIN
RESET_MAX_REQUESTS, RESET_WINDOW_SECONDS = 5, 15 * 60
logger = logging.getLogger(__name__)


def body(request):
    try:
        return json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return {}


def fail(code, message, status=400):
    return JsonResponse({'ok': False, 'error': code, 'message': message}, status=status)


def plan_json(plan):
    lines = list(plan.lines.all())
    return {
        'id': plan.pk, 'version': plan.version, 'status': plan.status, 'service_date': plan.service_date.isoformat(),
        'store': plan.store_id, 'forecast_total': round(sum(l.forecast_qty for l in lines) * (1 + plan.adjustment_pct / 100)),
        'applied_total': sum(l.applied_qty for l in lines), 'lines': len(lines),
        'short': sum(1 for l in lines if l.level == PrepLine.Level.SHORT),
        'topup': sum(1 for l in lines if l.level == PrepLine.Level.TOPUP),
        'adjustment_pct': plan.adjustment_pct, 'reason': plan.adjustment_reason,
    }


def my_plan(request, plan_id):
    """Đề xuất thuộc đúng cửa hàng của người gọi (chặn truy cập chéo cửa hàng)."""
    return get_object_or_404(PrepPlan, pk=plan_id, store=request.user.profile.store)


# ----------------------------------------------------------------------------- dự báo & duyệt
@require_POST
@api_role_required(MANAGER)
def run_forecast(request):
    config = SystemConfig.get()
    if not config.managers_can_run:
        return fail('disabled', 'Quản trị viên đã tắt quyền chạy dự báo của quản lý.', 403)
    service_date = parse_date(body(request).get('date'), plans.service_date_of(config))
    try:
        plan = plans.create_plan(request.user.profile.store, service_date, request.user, config)
    except plans.PlanError as exc:
        resp = fail(exc.code, str(exc), 409 if exc.code == 'approved' else 400)
        if exc.code == 'approved':                              # để giao diện mở lại đúng danh sách
            current = plans.working_plan(request.user.profile.store, service_date)
            resp = JsonResponse({'ok': False, 'error': 'approved', 'message': str(exc), 'plan_id': current.pk}, status=409)
        return resp
    except Exception:                                           # lỗi hệ thống (MySQL, mô hình…): ghi log, không lộ chi tiết
        logger.exception('Chạy dự báo lỗi: %s %s', request.user.profile.store_id, service_date)
        return fail('server_error', 'Không thể chạy dự báo do lỗi hệ thống · Thử lại sau ít phút hoặc báo quản trị viên.', 500)
    return JsonResponse({'ok': True, 'plan': plan_json(plan)})


@require_GET
@api_role_required(MANAGER)
def plan_detail(request, plan_id):
    plan = my_plan(request, plan_id)
    lines = list(plan.lines.select_related('product').order_by('-forecast_qty'))
    pct = plan.adjustment_pct
    return JsonResponse({
        'ok': True, 'plan': plan_json(plan), 'store_name': f'{plan.store_id} · {plan.store.restaurant_name}',
        'original_total': sum(l.need_qty for l in lines),
        'approved_by': (plan.approved_by.first_name or plan.approved_by.username) if plan.approved_by else '',
        'approved_at': timezone.localtime(plan.approved_at).strftime('%d/%m/%Y %H:%M') if plan.approved_at else '',
        'reopened': plan.reopened_at is not None,
        'lines': [{'name': l.product.menu_item_name, 'unit': unit_for(l.product), 'forecast': plans.adjusted_forecast(l.forecast_qty, pct),
                   'baseline': l.baseline_qty,
                   'diff': round((l.forecast_qty * (1 + pct / 100) - l.baseline_qty) / l.baseline_qty * 100) if l.baseline_qty else 0}
                  for l in lines],
    })


@require_POST
@api_role_required(MANAGER)
def adjust_plan(request, plan_id):
    plan, data = my_plan(request, plan_id), body(request)
    try:
        plans.set_adjustment(plan, int(data.get('pct', 0)), str(data.get('reason', '')))
    except (TypeError, ValueError):
        return fail('invalid', 'Tỷ lệ điều chỉnh không hợp lệ.')
    except plans.PlanError as exc:
        return fail(exc.code, str(exc), 409 if exc.code == 'not_pending' else 400)
    return JsonResponse({'ok': True, 'plan': plan_json(plan)})


@require_POST
@api_role_required(MANAGER)
def adjust_line(request, line_id):
    line = get_object_or_404(PrepLine.objects.select_related('plan'), pk=line_id, plan__store=request.user.profile.store)
    try:
        plans.set_line_qty(line, int(body(request).get('qty', -1)))
    except (TypeError, ValueError):
        return fail('invalid', 'Số lượng không hợp lệ.')
    except plans.PlanError as exc:
        return fail(exc.code, str(exc), 409 if exc.code == 'not_pending' else 400)
    return JsonResponse({'ok': True, 'qty': line.applied_qty, 'plan': plan_json(line.plan)})


@require_POST
@api_role_required(MANAGER)
def approve_plan(request, plan_id):
    try:
        plan = plans.approve(my_plan(request, plan_id), request.user)
    except plans.PlanError as exc:
        return fail(exc.code, str(exc), 409)
    return JsonResponse({'ok': True, 'plan': plan_json(plan), 'approved_at': timezone.localtime(plan.approved_at).strftime('%d/%m/%Y %H:%M')})


@require_POST
@api_role_required(MANAGER)
def reopen_plan(request, plan_id):
    try:
        plan = plans.reopen(my_plan(request, plan_id))
    except plans.PlanError as exc:
        return fail(exc.code, str(exc), 409)
    return JsonResponse({'ok': True, 'plan': plan_json(plan)})


# ----------------------------------------------------------------------------- nhân viên
@require_GET
@api_role_required(MANAGER)
def line_reason(request, line_id):
    line = get_object_or_404(PrepLine.objects.select_related('plan', 'product'), pk=line_id, plan__store=request.user.profile.store)
    return JsonResponse({'ok': True, **insights.line_insights(line)})


@require_POST
@api_role_required(STAFF)
def line_done(request, line_id):
    line = get_object_or_404(PrepLine.objects.select_related('plan'), pk=line_id, plan__store=request.user.profile.store)
    try:
        plans.mark_done(line, request.user, bool(body(request).get('done', True)))
    except plans.PlanError as exc:
        return fail(exc.code, str(exc), 409)
    return JsonResponse({'ok': True})


@require_POST
@api_role_required(STAFF)
def save_inventory(request):
    data = body(request)
    day = parse_date(data.get('date'), None)
    config = SystemConfig.get()
    if day != config.operating_date:
        return fail('invalid_date', 'Chỉ nhập kiểm kho cho ngày vận hành hiện tại.')
    quantities = {}
    for pid, q in (data.get('quantities') or {}).items():
        try:
            quantities[pid] = None if q in (None, '') else int(q)
        except (TypeError, ValueError):
            return fail('invalid', 'Số lượng không hợp lệ.')
    try:
        count, plan = plans.save_inventory(request.user.profile.store, day, request.user, quantities,
                                           draft=bool(data.get('draft')), config=config)
    except plans.PlanError as exc:
        return fail(exc.code, str(exc))
    entered = count.items.exclude(quantity=None).count()
    return JsonResponse({'ok': True, 'status': count.status, 'entered': entered,
                         'at': timezone.localtime(count.updated_at).strftime('%d/%m/%Y %H:%M'),
                         'plan': plan_json(plan) if plan else None})


# ----------------------------------------------------------------------------- thông báo & hồ sơ
def _notifications(user):
    return visible_for(user)


@require_GET
@api_role_required(MANAGER, STAFF, ADMIN)
def notifications(request):
    items = [{'id': n.pk, 'title': n.title, 'detail': n.detail, 'link': n.link, 'read': n.read_by.filter(pk=request.user.pk).exists()}
             for n in _notifications(request.user)[:20]]
    return JsonResponse({'ok': True, 'items': items})


@require_POST
@api_role_required(MANAGER, STAFF, ADMIN)
def read_notifications(request):
    for n in _notifications(request.user).exclude(read_by=request.user):
        n.read_by.add(request.user)
    return JsonResponse({'ok': True})


@require_POST
@api_role_required(MANAGER, STAFF, ADMIN)
def change_password(request):
    data = body(request)
    cur, new, again = data.get('current', ''), data.get('new', ''), data.get('again', '')
    if not request.user.check_password(cur):
        return fail('wrong_password', 'Mật khẩu hiện tại không đúng.')
    if not new or new != again:
        return fail('mismatch', 'Mật khẩu mới và xác nhận không khớp.')
    try:
        validate_password(new, request.user)
    except ValidationError as exc:
        return fail('weak_password', ' '.join(exc.messages))
    request.user.set_password(new)
    request.user.save()
    update_session_auth_hash(request, request.user)
    return JsonResponse({'ok': True, 'at': timezone.localtime().strftime('%d/%m/%Y %H:%M')})


@require_POST
@api_role_required(MANAGER, STAFF, ADMIN)
def save_prefs(request):
    data, p = body(request), request.user.profile
    for field in ('notify_new_plan', 'remind_inventory', 'weekly_email'):
        if field in data:
            setattr(p, field, bool(data[field]))
    p.save()
    return JsonResponse({'ok': True})


@require_POST
def password_reset_request(request):
    """Công khai (người dùng chưa đăng nhập): ghi nhận yêu cầu để quản trị viên xử lý.
    Luôn trả cùng một câu (không cho dò tên đăng nhập nào có thật) và giới hạn số lần gửi theo địa chỉ máy."""
    username = str(body(request).get('username', '')).strip()
    if not username:
        return fail('missing', 'Nhập tên đăng nhập.')
    key = f'pw-reset:{request.META.get("REMOTE_ADDR", "")}'
    if cache.get(key, 0) >= RESET_MAX_REQUESTS:
        return fail('too_many', 'Đã gửi quá nhiều yêu cầu · Thử lại sau 15 phút.', 429)
    cache.set(key, cache.get(key, 0) + 1, RESET_WINDOW_SECONDS)
    title = f'Yêu cầu cấp lại mật khẩu: {username}'
    if User.objects.filter(username=username, is_active=True).exists() and \
            not Notification.objects.filter(kind=Notification.Kind.DATA, role=ADMIN, title=title).exists():
        Notification.objects.create(kind=Notification.Kind.DATA, role=ADMIN, title=title,
                                    detail=f'Chờ xử lý · {timezone.localtime():%d/%m/%Y %H:%M}', link='accounts')
    return JsonResponse({'ok': True, 'at': timezone.localtime().strftime('%d/%m/%Y %H:%M')})
