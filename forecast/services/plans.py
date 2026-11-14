import logging
import math
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from forecast.models import (InventoryCount, InventoryItem, Notification, PrepLine, PrepPlan, Product, Profile, Role,
                             Store, SystemConfig, WeatherEvent)
from forecast.services import engine
from forecast.services.notifications import notify
from Utils import Config

logger = logging.getLogger(__name__)


class PlanError(Exception):

    def __init__(self, code, message=''):
        super().__init__(message or code)
        self.code = code


def forecast_range():
    return date.fromisoformat(Config.VAL_START), date.fromisoformat(Config.TEST_END)


def service_date_of(config=None):
    config = config or SystemConfig.get()
    return config.operating_date + timedelta(days=1)


def latest_saved_inventory(store, on_or_before):
    return (InventoryCount.objects.filter(store=store, status=InventoryCount.Status.SAVED, count_date__lte=on_or_before)
            .order_by('-count_date', '-created_at').first())


def working_plan(store, service_date):
    return PrepPlan.objects.filter(store=store, service_date=service_date).exclude(
        status=PrepPlan.Status.SUPERSEDED).order_by('-version').first()


def kitchen_plan(store, service_date, config=None):
    config = config or SystemConfig.get()
    qs = PrepPlan.objects.filter(store=store, service_date=service_date)
    qs = qs.filter(status=PrepPlan.Status.APPROVED) if config.require_approval else qs.exclude(status=PrepPlan.Status.SUPERSEDED)
    return qs.order_by('-version').first()


def is_locked(plan, config=None):
    config = config or SystemConfig.get()
    return bool(config.require_approval and plan and plan.status == PrepPlan.Status.APPROVED and plan.reopened_at is None)


def actionable_lines(plan):
    return plan.lines.filter(applied_qty__gt=0)


def is_complete(plan):
    lines = actionable_lines(plan)
    return plan.status == PrepPlan.Status.APPROVED and lines.exists() and not lines.filter(done_at=None).exists()


def level_of(need, current, safety):
    if need <= 0:
        return PrepLine.Level.OK
    return PrepLine.Level.SHORT if current < safety else PrepLine.Level.TOPUP


ADJUSTMENT_LEVELS = (-30, -15, 0, 15, 30)


def adjusted_forecast(forecast, pct=0):
    return (int(forecast) * (100 + int(pct)) + 50) // 100


def compute_line(forecast, safety, current, pct=0):
    need = max(0, adjusted_forecast(forecast, pct) + safety - current)
    return need, level_of(need, current, safety)


def is_manual(line):
    return line.applied_qty != line.need_qty


def recalc_plan(plan):
    lines = list(plan.lines.all())
    for ln in lines:
        manual = is_manual(ln)
        need, level = compute_line(ln.forecast_qty, ln.safety_stock, ln.current_stock, plan.adjustment_pct)
        ln.need_qty, ln.level = need, level
        if not manual:
            ln.applied_qty = need
    PrepLine.objects.bulk_update(lines, ['need_qty', 'applied_qty', 'level'])


@transaction.atomic
def create_plan(store, service_date, user, config=None):
    config = config or SystemConfig.get()
    first, last = forecast_range()
    if service_date < first:
        raise PlanError('train_data', f'Ngày {service_date:%d/%m/%Y} thuộc dữ liệu huấn luyện của mô hình, '
                                      f'không dự báo. Chọn ngày từ {first:%d/%m/%Y} đến {last:%d/%m/%Y}.')


    Store.objects.select_for_update().filter(pk=store.pk).first()
    current = (PrepPlan.objects.select_for_update().filter(store=store, service_date=service_date)
               .exclude(status=PrepPlan.Status.SUPERSEDED).order_by('-version').first())
    if is_locked(current, config):
        raise PlanError('approved', 'Danh sách đã duyệt – cần mở lại trước khi chạy lại dự báo.')

    inv = latest_saved_inventory(store, config.operating_date)
    if inv is None:
        raise PlanError('no_inventory', 'Chưa có kiểm kho để tính lượng cần chuẩn bị.')

    try:
        df = engine.forecast_store(store.pk, service_date, z=config.z)
    except engine.NoForecastData as exc:
        raise PlanError('no_data', 'Không có dữ liệu đầu vào cho ngày đã chọn.') from exc

    stock = {i.product_id: i.quantity for i in inv.items.all() if i.quantity is not None}
    products = {p.pk: p for p in Product.objects.all()}
    version = (PrepPlan.objects.select_for_update().filter(store=store, service_date=service_date).order_by('-version')
               .values_list('version', flat=True).first() or 0) + 1
    if current:
        PrepPlan.objects.filter(store=store, service_date=service_date,
                                status=PrepPlan.Status.PENDING).update(status=PrepPlan.Status.SUPERSEDED)


    pct, reason = (current.adjustment_pct, current.adjustment_reason) if current else (0, '')
    manual = {l.product_id: l.applied_qty for l in current.lines.all() if is_manual(l)} if current else {}
    plan = PrepPlan.objects.create(store=store, service_date=service_date, version=version,
                                   model_name=df['model_name'].iloc[0], inventory_count=inv, created_by=user,
                                   adjustment_pct=pct, adjustment_reason=reason)
    lines, raw_stock, raw_need = [], [], []
    for r in df.itertuples(index=False):
        fc, safe = round(r.predicted_qty), math.ceil(r.safety_stock)
        cur = stock.get(r.menu_item_id, 0)
        need, level = compute_line(fc, safe, cur, pct)
        lines.append(PrepLine(plan=plan, product=products[r.menu_item_id], forecast_qty=fc,
                              baseline_qty=round(r.baseline_qty) if r.baseline_qty == r.baseline_qty else 0,
                              safety_stock=safe, current_stock=cur, need_qty=need,
                              applied_qty=manual.get(r.menu_item_id, need), level=level))
        raw_stock.append(cur)
        raw_need.append(need)
    PrepLine.objects.bulk_create(lines)


    transaction.on_commit(lambda: _save_raw_forecasts(df, raw_stock, raw_need))

    if config.require_approval:
        notify(Notification.Kind.PLAN, Role.STAFF, store, 'Danh sách chuẩn bị đang chờ duyệt',
                f'Ngày phục vụ: {service_date:%d/%m/%Y}', 'staff_prep')
    else:
        _publish(plan, None)
    short = sum(1 for l in lines if l.level == PrepLine.Level.SHORT)
    if config.alert_red:
        notify(Notification.Kind.SHORTAGE, Role.MANAGER, store, f'Thiếu hàng: {short} món',
                f'{"Chờ duyệt" if config.require_approval else "Đã gửi bếp"} · {store.pk} · {timezone.localtime():%d/%m/%Y %H:%M}', 'prep')
    event = WeatherEvent.objects.filter(restaurant=store, event_date=service_date).first()
    if event and (event.is_special_event or event.is_holiday):
        notify(Notification.Kind.EVENT, Role.MANAGER, store, f'Sự kiện: {event.special_event_name or event.holiday_name}',
                f'Ngày phục vụ: {service_date:%d/%m/%Y}', 'forecast')
    return plan


def _save_raw_forecasts(df, raw_stock, raw_need):
    try:
        engine.save_raw_forecasts(df, raw_stock, raw_need)
    except Exception:
        logger.exception('Không ghi được bảng forecasts (đề xuất vẫn được tạo)')


@transaction.atomic
def set_adjustment(plan, pct, reason):
    if plan.status != PrepPlan.Status.PENDING:
        raise PlanError('not_pending', 'Chỉ điều chỉnh được đề xuất đang chờ duyệt.')
    if pct not in ADJUSTMENT_LEVELS:
        raise PlanError('invalid', 'Tỷ lệ điều chỉnh chỉ nhận −30%, −15%, 0%, +15% hoặc +30%.')
    if pct != 0 and not reason.strip():
        raise PlanError('reason_required', 'Cần nhập lý do điều chỉnh.')
    plan.adjustment_pct, plan.adjustment_reason = pct, reason.strip()
    plan.save(update_fields=['adjustment_pct', 'adjustment_reason'])
    recalc_plan(plan)
    return plan


def set_line_qty(line, qty):
    if line.plan.status != PrepPlan.Status.PENDING:
        raise PlanError('not_pending', 'Chỉ chỉnh số lượng khi đề xuất đang chờ duyệt.')
    if qty < 0:
        raise PlanError('invalid', 'Số lượng không âm.')
    line.applied_qty = qty
    line.save(update_fields=['applied_qty'])
    return line


def _publish(plan, user):
    PrepPlan.objects.filter(store=plan.store, service_date=plan.service_date,
                            status=PrepPlan.Status.APPROVED).exclude(pk=plan.pk).update(status=PrepPlan.Status.SUPERSEDED)
    plan.status, plan.approved_by, plan.approved_at = PrepPlan.Status.APPROVED, user, timezone.now()
    plan.save(update_fields=['status', 'approved_by', 'approved_at'])
    notify(Notification.Kind.PLAN, Role.STAFF, plan.store, 'Danh sách chuẩn bị đã được duyệt',
            f'Ngày phục vụ: {plan.service_date:%d/%m/%Y}', 'staff_prep')


@transaction.atomic
def approve(plan, user):
    if plan.status != PrepPlan.Status.PENDING:
        raise PlanError('not_pending', 'Đề xuất không ở trạng thái chờ duyệt.')
    _publish(plan, user)
    return plan


def reopen(plan):
    if plan.status != PrepPlan.Status.APPROVED:
        raise PlanError('not_approved', 'Danh sách chưa được duyệt.')
    plan.reopened_at = timezone.now()
    plan.save(update_fields=['reopened_at'])
    return plan


def mark_done(line, user, done=True):
    plan = line.plan
    if plan.status != PrepPlan.Status.APPROVED:
        raise PlanError('not_approved', 'Chỉ đánh dấu xong với danh sách đã gửi bếp.')
    line.done_by, line.done_at = (user, timezone.now()) if done else (None, None)
    line.save(update_fields=['done_by', 'done_at'])
    if done and is_complete(plan):
        notify(Notification.Kind.PREP, Role.MANAGER, plan.store, 'Chuẩn bị hàng đã hoàn tất',
                f'{user.first_name or user.username} · {timezone.localtime():%d/%m/%Y %H:%M}', 'prep')
    return line


def send_inventory_reminders(now=None, config=None):
    config, now = config or SystemConfig.get(), timezone.localtime(now)
    if now.time() < config.inventory_reminder:
        return 0
    sent = 0
    for store in Store.objects.filter(pk__in=Profile.objects.filter(role=Role.STAFF).values('store')):
        if not InventoryCount.objects.filter(store=store, count_date=config.operating_date,
                                             status=InventoryCount.Status.SAVED).exists():
            notify(Notification.Kind.REMINDER, Role.STAFF, store, 'Nhắc kiểm kho cuối ca',
                    f'Chưa lưu kiểm kho ngày {config.operating_date:%d/%m/%Y}', 'inventory')
            sent += 1
    return sent


def inventory_progress(items):
    entered = sum(1 for i in items if i.quantity is not None)
    review = sum(1 for i in items if i.needs_review)
    return entered, review, len(items) - entered


@transaction.atomic
def save_inventory(store, count_date, user, quantities, draft, config=None):
    config = config or SystemConfig.get()
    products = list(Product.objects.all())
    known = {p.pk for p in products}
    for pid in quantities:
        if pid not in known:
            raise PlanError('invalid', f'Món không tồn tại: {pid}')
    for q in quantities.values():
        if q is not None and q < 0:
            raise PlanError('invalid', 'Số lượng không âm.')

    prev = latest_saved_inventory(store, count_date - timedelta(days=1))
    prev_qty = {i.product_id: i.quantity for i in prev.items.all()} if prev else {}

    if not draft:
        missing = [p.pk for p in products if quantities.get(p.pk) is None]
        if missing:
            raise PlanError('incomplete', f'Còn {len(missing)} món chưa nhập số lượng.')

    status = InventoryCount.Status.DRAFT if draft else InventoryCount.Status.SAVED
    if draft:
        count = InventoryCount.objects.filter(store=store, count_date=count_date, status=status).first()
        if count:
            count.items.all().delete()
            count.user = user
            count.save()
        else:
            count = InventoryCount.objects.create(store=store, count_date=count_date, status=status, user=user)
    else:
        count = InventoryCount.objects.create(store=store, count_date=count_date, status=status, user=user)
        InventoryCount.objects.filter(store=store, count_date=count_date,
                                      status=InventoryCount.Status.DRAFT).delete()

    InventoryItem.objects.bulk_create([
        InventoryItem(count=count, product=p, quantity=quantities.get(p.pk), prev_quantity=prev_qty.get(p.pk))
        for p in products])

    plan = None
    if not draft:
        notify(Notification.Kind.INVENTORY, Role.MANAGER, store, 'Kiểm kho đã hoàn tất',
                f'{user.first_name or user.username} · {timezone.localtime():%d/%m/%Y %H:%M}', 'prep')
        service_date = count_date + timedelta(days=1)
        if config.auto_plan_after_inventory and count_date == config.operating_date:
            try:
                plan = create_plan(store, service_date, user, config)
            except PlanError:
                plan = None
    return count, plan
