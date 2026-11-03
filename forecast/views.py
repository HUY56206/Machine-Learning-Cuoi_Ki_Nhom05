"""Các trang HTML. Nghiệp vụ nằm ở forecast/services; thao tác ghi đi qua forecast/api.py."""
import csv
import json
from collections import OrderedDict
from datetime import date, datetime, timedelta

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField, Min, Sum
from django.db.models.functions import ExtractWeekDay, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from forecast.models import (DailySale, InventoryCount, InventoryItem, PrepLine, PrepPlan, Product, Profile, Promotion,
                             Role, Store, SystemConfig, WeatherEvent)
from forecast.permissions import HOME, role_required
from forecast.services import adminops, engine, plans
from forecast.services.units import unit_for

MANAGER, STAFF, ADMIN = Role.MANAGER, Role.STAFF, Role.ADMIN
PAGE_SIZE = 5
LOGIN_MAX_FAILS, LOGIN_LOCK_SECONDS = 5, 15 * 60


# ----------------------------------------------------------------------------- tiện ích
def parse_date(text, default=None):
    """'31/10/2025' hoặc '2025-10-31' -> date; sai định dạng -> default."""
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, fmt).date()
        except (TypeError, ValueError):
            continue
    return default


def page(request, template, active, **ctx):
    return render(request, f'forecast/{template}.html', {'active_menu': active, **ctx})


def attach_units(lines):
    for ln in lines:
        ln.unit = unit_for(ln.product)
    return lines


# ----------------------------------------------------------------------------- đăng nhập / chung
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        key = f'login-fail:{username.lower()}:{request.META.get("REMOTE_ADDR", "")}'
        if cache.get(key, 0) >= LOGIN_MAX_FAILS:                       # khóa tạm khi sai nhiều lần
            return JsonResponse({'ok': False, 'error': 'locked'}, status=429)
        user = authenticate(request, username=username, password=request.POST.get('password', ''))
        if user is None or not hasattr(user, 'profile'):
            cache.set(key, cache.get(key, 0) + 1, LOGIN_LOCK_SECONDS)
            return JsonResponse({'ok': False, 'error': 'invalid_credentials'}, status=400)
        cache.delete(key)
        auth_login(request, user)
        if not request.POST.get('remember'):
            request.session.set_expiry(0)                             # không nhớ: hết phiên khi đóng trình duyệt
        target = request.POST.get('next', '')
        if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
            target = ''
        return JsonResponse({'ok': True, 'next': target or reverse(HOME[user.profile.role])})
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        return redirect(HOME[request.user.profile.role])
    accounts = [{'value': p.user.username, 'label': f'{p.user.username} · {p.get_role_display()}'}
                for p in Profile.objects.select_related('user').filter(user__is_active=True).order_by('role', 'user__username')]
    return render(request, 'forecast/login.html', {'accounts': accounts, 'accounts_json': json.dumps(accounts, ensure_ascii=False),
                                                   'next': request.GET.get('next', '')})


@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect('forecast:login')


def home(request):
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        return redirect(HOME[request.user.profile.role])
    return redirect('forecast:login')


@role_required(MANAGER, STAFF, ADMIN)
def profile(request):
    p = request.user.profile
    info = {
        'initial': (p.user.first_name or p.user.username)[:1].upper(),
        'name': p.user.first_name or p.user.username,
        'role_name': p.get_role_display(),
        'user': p.user.username,
        'store': f'{p.store.pk} – {p.store.restaurant_name}' if p.store else 'Toàn hệ thống',
    }
    return page(request, 'profile', 'profile', profile=info)


def no_access(request):
    return render(request, 'forecast/no_access.html', {'active_menu': 'none'})


# ----------------------------------------------------------------------------- quản lý · Tổng quan
@role_required(MANAGER)
def dashboard(request):
    store, config = request.user.profile.store, SystemConfig.get()
    day = parse_date(request.GET.get('date'), plans.service_date_of(config))
    plan = plans.working_plan(store, day)

    days = [day - timedelta(days=i) for i in range(6, 0, -1)]
    actual = dict(DailySale.objects.filter(restaurant=store, sale_date__in=[d for d in days if d <= config.operating_date])
                  .values('sale_date').annotate(t=Sum('quantity')).values_list('sale_date', 't'))
    bars = [{'label': d, 'value': actual.get(d), 'forecast': False} for d in days]
    forecast_total = None
    if plan:
        forecast_total = round(sum(l.forecast_qty for l in plan.lines.all()) * (1 + plan.adjustment_pct / 100))
    bars.append({'label': day, 'value': forecast_total, 'forecast': True})
    top = max([b['value'] or 0 for b in bars] + [1])
    for b in bars:
        b['height'] = round((b['value'] or 0) / top * 100)

    counts = {'short': 0, 'topup': 0, 'ok': 0}
    todo = None
    if plan:
        for row in plan.lines.values('level').annotate(n=Count('id')):
            counts[row['level']] = row['n']
        todo = Paginator(plan.lines.filter(level=PrepLine.Level.SHORT).select_related('product'), PAGE_SIZE).get_page(request.GET.get('page'))
        attach_units(todo.object_list)
    return page(request, 'dashboard', 'dashboard', day=day, plan=plan, bars=bars, counts=counts, todo=todo, config=config,
                no_data=plan is None and day != plans.service_date_of(config))


# ----------------------------------------------------------------------------- quản lý · Chuẩn bị hàng
def _prep_context(request):
    store, config = request.user.profile.store, SystemConfig.get()
    day = parse_date(request.GET.get('date'), plans.service_date_of(config))
    return store, config, day, plans.working_plan(store, day)


@role_required(MANAGER)
def prep(request):
    store, config, day, plan = _prep_context(request)
    level = request.GET.get('level', 'short')
    counts = {'all': 0, 'short': 0, 'topup': 0, 'ok': 0}
    lines_page = None
    if plan:
        for row in plan.lines.values('level').annotate(n=Count('id')):
            counts[row['level']] = row['n']
        counts['all'] = sum(counts.values())
        qs = plan.lines.select_related('product')
        if level in counts and level != 'all':
            qs = qs.filter(level=level)
        else:
            level = 'all'
        lines_page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get('page'))
        attach_units(lines_page.object_list)
    return page(request, 'prep', 'prep', day=day, plan=plan, level=level, counts=counts, lines=lines_page, config=config,
                locked=plans.is_locked(plan, config), complete=bool(plan and plans.is_complete(plan)))


@role_required(MANAGER)
def prep_export(request):
    """Tải danh sách chuẩn bị dạng CSV (mở được bằng Excel)."""
    store, config, day, plan = _prep_context(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="chuan_bi_{store.pk}_{day:%Y%m%d}.csv"'
    response.write('﻿')                                          # BOM để Excel đọc đúng tiếng Việt
    w = csv.writer(response)
    w.writerow(['Món', 'Đơn vị', 'Dự báo', 'Tồn an toàn', 'Tồn hiện tại', 'Cần chuẩn bị', 'Trạng thái'])
    if plan:
        for ln in attach_units(list(plan.lines.select_related('product'))):
            w.writerow([ln.product.menu_item_name, ln.unit, ln.forecast_qty, ln.safety_stock, ln.current_stock,
                        ln.applied_qty, ln.get_level_display()])
    return response


# ----------------------------------------------------------------------------- quản lý · Dự báo
@role_required(MANAGER)
def forecast(request):
    store, config = request.user.profile.store, SystemConfig.get()
    day = parse_date(request.GET.get('date'), plans.service_date_of(config))
    plan = plans.working_plan(store, day)

    cards = []
    for i in range(3):
        d = plans.service_date_of(config) + timedelta(days=i)
        p = plans.working_plan(store, d)
        total = round(sum(l.forecast_qty for l in p.lines.all()) * (1 + p.adjustment_pct / 100)) if p else None
        cards.append({'date': d, 'total': total, 'selected': d == day})

    lines_page, total, base_total = None, 0, 0
    if plan:
        qs = plan.lines.select_related('product').order_by('-forecast_qty')
        base_total = sum(l.forecast_qty for l in plan.lines.all())
        total = round(base_total * (1 + plan.adjustment_pct / 100))
        lines_page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get('page'))
        for ln in attach_units(lines_page.object_list):
            adj = ln.forecast_qty * (1 + plan.adjustment_pct / 100)
            ln.shown = round(adj)
            ln.diff = round((adj - ln.baseline_qty) / ln.baseline_qty * 100) if ln.baseline_qty else 0

    weather = WeatherEvent.objects.filter(restaurant=store, event_date=day).first()
    promos = list(Promotion.objects.filter(restaurant=store, promo_date=day).select_related('product')
                  .values_list('product__menu_item_name', flat=True)[:3])
    factors = None
    if weather:
        sky = {'None': 'Khô ráo', 'Rain': 'Có mưa', 'Snow': 'Có tuyết'}.get(weather.precip_type, weather.precip_type)
        factors = {
            'event': weather.special_event_name if weather.is_special_event else None,
            'weather': f'{sky}, khoảng {round((float(weather.avg_temp_f) - 32) / 1.8)}°C',
            'holiday': weather.holiday_name if weather.is_holiday else None,
            'promos': promos,
        }
    return page(request, 'forecast', 'forecast', day=day, plan=plan, cards=cards, lines=lines_page, total=total, base_total=base_total,
                factors=factors, config=config, locked=plans.is_locked(plan, config))


# ----------------------------------------------------------------------------- quản lý · Báo cáo
PERIODS = OrderedDict([
    ('01/01/2025 – 30/10/2025', (date(2025, 1, 1), date(2025, 10, 30))),
    ('01/11/2025 – 30/11/2025', (date(2025, 11, 1), date(2025, 11, 30))),
])


def _bars(values, top_n=3, fmt=None):
    """values: list[(label, value)] -> dữ liệu vẽ cột, tô đậm top_n giá trị cao nhất."""
    vals = [v for _, v in values if v is not None]
    peak = max(vals + [1])
    ranked = sorted(vals, reverse=True)[:top_n]
    return [{'label': l, 'value': v, 'height': round(v / peak * 100) if v else 0, 'top': v in ranked}
            for l, v in values]


@role_required(MANAGER)
def report(request):
    store, config = request.user.profile.store, SystemConfig.get()
    period = request.GET.get('period', next(iter(PERIODS)))
    start, end = PERIODS.get(period, next(iter(PERIODS.values())))
    end = min(end, config.operating_date)                          # không lộ số bán sau ngày vận hành
    tab = 'accuracy' if request.GET.get('tab') == 'accuracy' else 'trend'
    ctx = {'period': period, 'periods': list(PERIODS), 'store': store, 'has_data': start <= end, 'tab': tab}
    if not ctx['has_data']:
        return page(request, 'report', 'report', **ctx)
    if tab == 'accuracy':
        ctx.update(_accuracy_context(store, config))
        return page(request, 'report', 'report', **ctx)

    rev = ExpressionWrapper(F('quantity') * F('product__unit_price'), output_field=FloatField())
    sales = DailySale.objects.filter(restaurant=store, sale_date__range=(start, end))
    monthly = list(sales.annotate(m=TruncMonth('sale_date')).values('m').annotate(r=Sum(rev), q=Sum('quantity')).order_by('m'))
    top_items = list(sales.values('product__menu_item_name').annotate(r=Sum(rev)).order_by('-r')[:3])
    by_qty = list(sales.values('product__menu_item_name').annotate(q=Sum('quantity')).order_by('-q'))

    history = DailySale.objects.filter(restaurant=store, sale_date__lte=end)
    by_month = {r['m']: r['a'] for r in history.annotate(m=F('sale_date__month')).values('m').annotate(a=Avg('quantity'))}
    by_dow = {r['d']: r['a'] for r in history.annotate(d=ExtractWeekDay('sale_date')).values('d').annotate(a=Avg('quantity'))}
    months = _bars([(f'T{m}', round(by_month[m], 1)) for m in sorted(by_month)])
    dows = [(2, 'T2'), (3, 'T3'), (4, 'T4'), (5, 'T5'), (6, 'T6'), (7, 'T7'), (1, 'CN')]   # Django: 1 = Chủ nhật
    weekdays = _bars([(l, round(by_dow[k], 1)) for k, l in dows if k in by_dow])
    best_month = max(by_month, key=by_month.get)
    best_dow = max(by_dow, key=by_dow.get)
    day_names = {2: 'Thứ Hai', 3: 'Thứ Ba', 4: 'Thứ Tư', 5: 'Thứ Năm', 6: 'Thứ Sáu', 7: 'Thứ Bảy', 1: 'Chủ nhật'}
    effects = _factor_effects(store.pk, end)
    ctx.update({
        'total_rev': sum(m['r'] for m in monthly), 'total_qty': sum(m['q'] for m in monthly),
        'rev_bars': _bars([(f'T{m["m"].month}', round(m['r'] / 1000)) for m in monthly], top_n=1),
        'top_items': top_items, 'best_items': by_qty[:3], 'worst_items': by_qty[-3:][::-1],
        'months': months, 'weekdays': weekdays, 'effects': effects,
        'best_month': (best_month, round(by_month[best_month], 1)),
        'best_dow': (day_names[best_dow], round(by_dow[best_dow], 1)),
        'event_lift': next((e['pct'] for e in effects if e['label'] == 'Sự kiện'), None),
        'history_end': end,
    })
    return page(request, 'report', 'report', **ctx)


def _accuracy_context(store, config):
    """Tab Độ chính xác dự báo: wMAPE từng ngày trong 7 ngày gần nhất tới ngày vận hành."""
    end = config.operating_date
    try:
        days = engine.accuracy_by_day(store.pk, end - timedelta(days=6), end)
    except Exception as exc:
        return {'acc_error': str(exc)}
    if not days:
        return {'acc': None}
    top = max(v for _, v in days)
    return {'acc': {'avg': round(sum(v for _, v in days) / len(days), 1), 'start': days[0][0], 'end': days[-1][0],
                    'bars': [{'label': d.strftime('%d/%m'), 'value': v, 'height': round(v / top * 120)} for d, v in days]}}


FACTORS = [('Sự kiện', 'w.is_special_event = 1'), ('Khuyến mãi', 'pr.promotion_id IS NOT NULL'),
           ('Cuối tuần', 'DAYOFWEEK(s.sale_date) IN (1, 7)'), ('Ngày lễ', 'w.is_holiday = 1'),
           ('Mưa', "w.precip_type = 'Rain'"), ('Tuyết', "w.precip_type = 'Snow'")]


def _factor_effects(store_id, end):
    """% chênh lệch bán trung bình giữa ngày/món có yếu tố và không có (cùng cửa hàng)."""
    cols = ', '.join(f'AVG(CASE WHEN {c} THEN s.quantity END), AVG(CASE WHEN NOT ({c}) THEN s.quantity END)' for _, c in FACTORS)
    with connection.cursor() as cur:
        cur.execute(
            f"""SELECT {cols} FROM daily_sales s
                JOIN weather_events w ON w.restaurant_id = s.restaurant_id AND w.event_date = s.sale_date
                LEFT JOIN promotions pr ON pr.restaurant_id = s.restaurant_id AND pr.menu_item_id = s.menu_item_id
                                       AND pr.promo_date = s.sale_date
                WHERE s.restaurant_id = %s AND s.sale_date <= %s""", [store_id, end])
        row = cur.fetchone()
    out = []
    for i, (label, _) in enumerate(FACTORS):
        yes, no = row[2 * i], row[2 * i + 1]
        out.append({'label': label, 'pct': round((float(yes) - float(no)) / float(no) * 100) if yes is not None and no else None})
    return out


# ----------------------------------------------------------------------------- nhân viên · Danh sách chuẩn bị
@role_required(STAFF)
def staff_prep(request):
    store, config = request.user.profile.store, SystemConfig.get()
    day = plans.service_date_of(config)
    plan = plans.kitchen_plan(store, day, config)
    ctx = {'day': day, 'plan': plan, 'config': config}
    if plan is None:                                              # NV-1 trạng thái "Chờ duyệt"
        waiting = plans.working_plan(store, day)
        ctx.update({'waiting': waiting, 'waiting_total': plans.actionable_lines(waiting).count() if waiting else 0})
    else:
        lines = attach_units(list(plan.lines.filter(applied_qty__gt=0).select_related('product')))
        ctx.update({
            'short': [l for l in lines if l.level == PrepLine.Level.SHORT and not l.done_at],
            'topup': [l for l in lines if l.level == PrepLine.Level.TOPUP and not l.done_at],
            'done': [l for l in lines if l.done_at],
            'total_lines': len(lines),
            'total_qty': sum(l.applied_qty for l in lines),
            'complete': plans.is_complete(plan),
        })
    return page(request, 'staff_prep', 'staff_prep', **ctx)


# ----------------------------------------------------------------------------- nhân viên · Kiểm kho
CATEGORY_LABELS = OrderedDict([
    ('Drinks', 'Đồ uống'), ('Burgers', 'Burger'), ('Chicken', 'Gà'), ('Sides', 'Món phụ'),
    ('Combos', 'Combo'), ('Breakfast', 'Bữa sáng'), ('Desserts', 'Tráng miệng'), ('Specials', 'Đặc biệt'),
])


@role_required(STAFF)
def inventory(request):
    store, config = request.user.profile.store, SystemConfig.get()
    day = parse_date(request.GET.get('date'), config.operating_date)
    draft = InventoryCount.objects.filter(store=store, count_date=day, status=InventoryCount.Status.DRAFT).first()
    saved = InventoryCount.objects.filter(store=store, count_date=day, status=InventoryCount.Status.SAVED).first()
    source = draft or saved
    current = {i.product_id: i.quantity for i in source.items.all()} if source else {}
    prev_count = plans.latest_saved_inventory(store, day - timedelta(days=1))
    prev = {i.product_id: i.quantity for i in prev_count.items.all()} if prev_count else {}

    products = list(Product.objects.all())
    rows = []
    for p in products:
        rows.append({'id': p.pk, 'name': p.menu_item_name, 'unit': unit_for(p), 'category': p.category,
                     'prev': prev.get(p.pk), 'cur': current.get(p.pk)})
    groups = []
    for key, label in CATEGORY_LABELS.items():
        items = [r for r in rows if r['category'] == key]
        groups.append({'key': key, 'label': label, 'total': len(items)})

    history = []
    for c in InventoryCount.objects.filter(store=store, status=InventoryCount.Status.SAVED).order_by('-created_at')[:3]:
        history.append({'at': c.created_at, 'entered': c.items.exclude(quantity=None).count(),
                        'user': (c.user.first_name or c.user.username) if c.user else ''})
    return page(request, 'inventory', 'inventory', day=day, rows=rows, groups=groups, history=history,
                source=source, readonly=day != config.operating_date)


# ----------------------------------------------------------------------------- quản trị viên
def _store_choices():
    return [f'{s.pk} · {s.restaurant_name}' for s in Store.objects.all()]


@role_required(ADMIN)
def data(request):
    config = SystemConfig.get()
    first = DailySale.objects.aggregate(a=Min('sale_date'))['a'] or config.operating_date
    default = f'{first:%d/%m/%Y} – {config.operating_date:%d/%m/%Y}'
    text = request.GET.get('range', default)
    parts = [parse_date(p.strip()) for p in text.split('–')]
    start, end = (parts + [None, None])[:2] if len(parts) == 2 else (None, None)
    if not start or not end or start > end:
        text, (start, end) = default, (first, config.operating_date)
    groups = Paginator(adminops.data_overview(start, end), PAGE_SIZE).get_page(request.GET.get('page'))
    return page(request, 'data', 'data', range_text=text, groups=groups, missing=adminops.missing_summary(start, end),
                start=start, end=end, operating_date=config.operating_date)


@role_required(ADMIN)
def model(request):
    config = SystemConfig.get()
    rows = adminops.store_runs(config)
    selected = Store.objects.filter(pk=request.GET.get('store')).first() or rows[0]['store']
    series = adminops.store_series(selected, config)
    values = [v for _, v in series['actual']] + ([series['forecast'][1]] if series['forecast'] else [])
    peak = max(values + [1])
    bars = [{'label': d, 'value': v, 'height': round(v / peak * 120), 'forecast': False} for d, v in series['actual']]
    if series['forecast']:
        bars.append({'label': series['forecast'][0], 'value': series['forecast'][1], 'height': round(series['forecast'][1] / peak * 120), 'forecast': True})
    sort = request.GET.get('sort', 'priority')
    if sort == 'code':
        rows.sort(key=lambda r: r['store'].pk)
    return page(request, 'model', 'model', info=adminops.model_info(), rows=Paginator(rows, 6).get_page(request.GET.get('page')),
                selected=selected, bars=bars, sort=sort, store_choices=_store_choices(), service_date=plans.service_date_of(config),
                operating_date=config.operating_date)


@role_required(ADMIN)
def stores(request):
    rows = adminops.stores_overview()
    managers = list(Profile.objects.filter(role=Role.MANAGER, user__is_active=True).select_related('user'))
    return page(request, 'stores', 'stores', rows=Paginator(rows, PAGE_SIZE).get_page(request.GET.get('page')),
                unassigned=sum(1 for r in rows if not r['manager']), total=len(rows),
                first_unassigned=next((r for r in rows if not r['manager']), None),
                manager_choices=['Chưa gán'] + [p.user.first_name or p.user.username for p in managers])


@role_required(ADMIN)
def accounts(request):
    rows = []
    for p in Profile.objects.select_related('user', 'store').order_by('role', 'user__username'):
        scope = f'{p.store.pk} · {p.store.restaurant_name}' if p.store else 'Toàn hệ thống'
        rows.append({'name': p.user.first_name or p.user.username, 'username': p.user.username, 'role': p.get_role_display(),
                     'scope': scope, 'active': p.user.is_active})
    counts = {label: sum(1 for r in rows if r['role'] == label) for _, label in Role.choices}
    return page(request, 'accounts', 'accounts', rows=rows, counts=counts, total=len(rows),
                scope_choices=_store_choices() + ['Toàn hệ thống'])


@role_required(ADMIN)
def config(request):
    return page(request, 'config', 'config', cfg=SystemConfig.get())
