import csv
import io
import re
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.db.models import Avg, Count, Max, Min, Sum
from django.utils import timezone

from forecast.models import (DailySale, Forecast, InventoryItem, Notification, PrepPlan, Product, Profile, Promotion, Role,
                             Store, SystemConfig, WeatherEvent)
from forecast.services import engine, plans
from forecast.services.notifications import notify
from Utils import Config


class AdminError(Exception):

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def missing_qs(start, end):
    return DailySale.objects.filter(sale_date__range=(start, end), quantity_raw__isnull=True)


def missing_summary(start, end):
    total = DailySale.objects.filter(sale_date__range=(start, end)).count()
    miss = missing_qs(start, end).count()
    return {'missing': miss, 'total': total, 'pct': round(miss / total * 100, 1) if total else 0}


def missing_rows(start, end, limit=50):
    return [{'date': r.sale_date.strftime('%d/%m/%Y'), 'store': r.restaurant_id, 'item': r.product.menu_item_name}
            for r in missing_qs(start, end).select_related('product').order_by('sale_date', 'restaurant_id')[:limit]]


def data_overview(start, end):
    sales = DailySale.objects.filter(sale_date__range=(start, end))
    span = sales.aggregate(a=Min('sale_date'), b=Max('sale_date'))
    summ = missing_summary(start, end)
    scope = f'{span["a"]:%d/%m/%Y} – {span["b"]:%d/%m/%Y}' if span['a'] else 'Chưa có dữ liệu'
    weather = WeatherEvent.objects.filter(event_date__range=(start, end))
    events = weather.filter(is_holiday=True).count() + weather.filter(is_special_event=True).count()
    ok, bad = 'Bình thường', 'Thiếu dữ liệu'
    return [
        {'key': 'sales', 'name': 'Bán hàng hằng ngày', 'rows': summ['total'], 'scope': scope, 'impact': 'Dự báo của mọi cửa hàng',
         'status': bad if summ['missing'] else ok, 'fields': 'Ngày bán · Cửa hàng · Món · Số lượng bán', 'import': True},
        {'key': 'promo', 'name': 'Khuyến mãi', 'rows': Promotion.objects.filter(promo_date__range=(start, end)).count(),
         'scope': 'Món / cửa hàng', 'impact': 'Dự báo của món có khuyến mãi', 'status': ok,
         'fields': 'Ngày · Cửa hàng · Món · Chương trình khuyến mãi', 'import': True},
        {'key': 'weather', 'name': 'Thời tiết', 'rows': weather.count(), 'scope': scope,
         'impact': 'Dự báo của cửa hàng trong thành phố', 'status': ok,
         'fields': 'Ngày · Cửa hàng · Nhiệt độ · Điều kiện thời tiết', 'import': True},
        {'key': 'holiday', 'name': 'Ngày lễ & sự kiện', 'rows': events, 'scope': 'Ngày lễ và sự kiện', 'impact': 'Dự báo các ngày có sự kiện',
         'status': ok, 'fields': 'Ngày · Cửa hàng · Ngày lễ · Sự kiện', 'import': True},
        {'key': 'stock', 'name': 'Kiểm kho', 'rows': InventoryItem.objects.filter(count__count_date__range=(start, end), quantity__isnull=False).count(),
         'scope': 'Theo từng ca', 'impact': 'Đề xuất chuẩn bị hàng', 'status': ok,
         'fields': 'Ngày kiểm kho · Cửa hàng · Món · Số lượng còn lại', 'import': False,
         'note': 'Kiểm kho được cập nhật khi nhân viên lưu số lượng còn lại.'},
        {'key': 'forecast', 'name': 'Kết quả dự báo', 'rows': Forecast.objects.filter(forecast_date__range=(start, end)).count(),
         'scope': 'Tạo khi chạy dự báo', 'impact': 'Đề xuất chuẩn bị hàng', 'status': ok,
         'fields': 'Ngày dự báo · Cửa hàng · Món · Số lượng dự báo', 'import': False},
    ]


def refresh_data_notification(config=None):
    config = config or SystemConfig.get()
    n = missing_qs('2000-01-01', config.operating_date).count()
    Notification.objects.filter(kind=Notification.Kind.DATA, role=Role.ADMIN, title__startswith='Dữ liệu thiếu').delete()
    if n:
        notify(Notification.Kind.DATA, Role.ADMIN, None, f'Dữ liệu thiếu số lượng: {n:,} dòng'.replace(',', '.'),
               f'Phạm vi: {Store.objects.count()} cửa hàng · {timezone.localtime():%d/%m/%Y %H:%M}', 'data')
    return n


MAX_IMPORT_ROWS, MAX_IMPORT_BYTES = 200_000, 20 * 1024 * 1024
DATE_FORMATS = ('%Y-%m-%d', '%d/%m/%Y')
GROUP_COLUMNS = {
    'Bán hàng hằng ngày': ['sale_date', 'restaurant_id', 'menu_item_id', 'quantity'],
    'Khuyến mãi': ['promo_date', 'restaurant_id', 'menu_item_id'],
    'Thời tiết': ['event_date', 'restaurant_id', 'avg_temp_f', 'precip_type'],
    'Ngày lễ & sự kiện': ['event_date', 'restaurant_id'],
}
MODES = ('Thêm dữ liệu mới', 'Cập nhật theo khóa')


def read_table(filename, raw):
    if len(raw) > MAX_IMPORT_BYTES:
        raise AdminError('too_large', 'Tệp vượt quá 20 MB.')
    name = filename.lower()
    try:
        if name.endswith('.csv'):
            reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
            rows = [{(k or '').strip(): (v or '').strip() for k, v in r.items()} for r in reader]
            cols = [c.strip() for c in (reader.fieldnames or [])]
        elif name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(raw), dtype=str).fillna('')
            cols = [str(c).strip() for c in df.columns]
            rows = [{str(k).strip(): str(v).strip() for k, v in r.items()} for r in df.to_dict('records')]
        else:
            raise AdminError('bad_file', 'Chọn tệp CSV hoặc Excel.')
    except AdminError:
        raise
    except Exception as exc:
        raise AdminError('bad_file', f'Không đọc được tệp: {exc}') from exc
    if len(rows) > MAX_IMPORT_ROWS:
        raise AdminError('too_large', f'Tệp quá {MAX_IMPORT_ROWS:,} dòng.'.replace(',', '.'))
    return cols, rows


def _date(v):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'ngày không hợp lệ "{v}"')


def _flag(v):
    if v.lower() in ('1', 'true', 'yes', 'có'):
        return 1
    if v.lower() in ('0', 'false', 'no', 'không', ''):
        return 0
    raise ValueError(f'giá trị 0/1 không hợp lệ "{v}"')


def _normalize(group, r, stores, products):
    store = r['restaurant_id']
    if store not in stores:
        raise ValueError(f'cửa hàng không tồn tại "{store}"')
    if group == 'Bán hàng hằng ngày':
        if r['menu_item_id'] not in products:
            raise ValueError(f'món không tồn tại "{r["menu_item_id"]}"')
        q = int(r['quantity'])
        if q < 0:
            raise ValueError('số lượng âm')
        return (_date(r['sale_date']), store, r['menu_item_id']), {'quantity': q}
    if group == 'Khuyến mãi':
        if r['menu_item_id'] not in products:
            raise ValueError(f'món không tồn tại "{r["menu_item_id"]}"')
        return (_date(r['promo_date']), store, r['menu_item_id']), {}
    key = (store, _date(r['event_date']))
    if group == 'Thời tiết':
        if r['precip_type'] not in ('None', 'Rain', 'Snow'):
            raise ValueError(f'precip_type không hợp lệ "{r["precip_type"]}"')
        return key, {'avg_temp_f': Decimal(r['avg_temp_f']), 'precip_inches': Decimal(r.get('precip_inches') or '0'),
                     'precip_type': r['precip_type'], 'is_holiday': _flag(r.get('is_holiday', '')),
                     'holiday_name': r.get('holiday_name') or None, 'is_special_event': _flag(r.get('is_special_event', '')),
                     'special_event_name': r.get('special_event_name') or None}
    return key, {'is_holiday': _flag(r.get('is_holiday', '')), 'holiday_name': r.get('holiday_name') or None,
                 'is_special_event': _flag(r.get('is_special_event', '')), 'special_event_name': r.get('special_event_name') or None}


def _existing(group, keys):
    if not keys:
        return set()
    with connection.cursor() as cur:
        if group == 'Bán hàng hằng ngày':
            tbl, cols, dcol = 'daily_sales', 'sale_date, restaurant_id, menu_item_id', 'sale_date'
        elif group == 'Khuyến mãi':
            tbl, cols, dcol = 'promotions', 'promo_date, restaurant_id, menu_item_id', 'promo_date'
        else:
            tbl, cols, dcol = 'weather_events', 'restaurant_id, event_date', 'event_date'
        dates = [k[0] if tbl != 'weather_events' else k[1] for k in keys]
        cur.execute(f'SELECT {cols} FROM {tbl} WHERE {dcol} BETWEEN %s AND %s', [min(dates), max(dates)])
        return {tuple(r) for r in cur.fetchall()}


def analyse_import(group, mode, filename, raw):
    if group not in GROUP_COLUMNS or mode not in MODES:
        raise AdminError('invalid', 'Nhóm dữ liệu hoặc cách nhập không hợp lệ.')
    cols, rows = read_table(filename, raw)
    missing_cols = [c for c in GROUP_COLUMNS[group] if c not in cols]
    out = {'file': filename, 'columns_ok': not missing_cols, 'missing_columns': missing_cols, 'total': len(rows),
           'errors': [], 'new': [], 'update': [], 'skipped': 0, 'invalid': 0, 'sample': rows[:5], 'columns': cols}
    if missing_cols:
        return out
    stores = set(Store.objects.values_list('pk', flat=True))
    products = set(Product.objects.values_list('pk', flat=True))
    parsed = {}
    for line, r in enumerate(rows, start=2):
        try:
            key, vals = _normalize(group, r, stores, products)
        except (ValueError, InvalidOperation, KeyError) as exc:
            out['invalid'] += 1
            if len(out['errors']) < 5:
                out['errors'].append(f'Dòng {line}: {exc}')
            continue
        if key in parsed:
            out['skipped'] += 1
            continue
        parsed[key] = vals
    exists = _existing(group, list(parsed))
    for key, vals in parsed.items():
        if key in exists:
            if mode == MODES[1] and group != 'Khuyến mãi':
                out['update'].append((key, vals))
            else:
                out['skipped'] += 1
        elif mode == MODES[0] and group != 'Ngày lễ & sự kiện':
            out['new'].append((key, vals))
        else:
            out['skipped'] += 1
    return out


@transaction.atomic
def commit_import(group, mode, filename, raw):
    res = analyse_import(group, mode, filename, raw)
    if not res['columns_ok']:
        raise AdminError('missing_columns', 'Thiếu cột bắt buộc: ' + ', '.join(res['missing_columns']))
    if not res['new'] and not res['update']:
        raise AdminError('nothing', 'Không có dòng hợp lệ nào để ghi.')
    with connection.cursor() as cur:
        if group == 'Bán hàng hằng ngày':
            cur.execute('SELECT COALESCE(MAX(sale_id), 0) FROM daily_sales')
            nxt = cur.fetchone()[0] + 1
            cur.executemany('INSERT INTO daily_sales (sale_id, sale_date, restaurant_id, menu_item_id, quantity, quantity_raw, is_imputed, is_outlier)'
                            ' VALUES (%s, %s, %s, %s, %s, %s, 0, 0)',
                            [(nxt + i, k[0], k[1], k[2], v['quantity'], v['quantity']) for i, (k, v) in enumerate(res['new'])])
            cur.executemany('UPDATE daily_sales SET quantity = %s, quantity_raw = %s, is_imputed = 0 WHERE sale_date = %s AND restaurant_id = %s AND menu_item_id = %s',
                            [(v['quantity'], v['quantity'], k[0], k[1], k[2]) for k, v in res['update']])
        elif group == 'Khuyến mãi':
            cur.executemany('INSERT INTO promotions (promo_date, restaurant_id, menu_item_id) VALUES (%s, %s, %s)', [k for k, _ in res['new']])
        else:
            cols = ['is_holiday', 'holiday_name', 'is_special_event', 'special_event_name']
            if group == 'Thời tiết':
                cols = ['avg_temp_f', 'precip_inches', 'precip_type'] + cols
                cur.executemany(f'INSERT INTO weather_events (restaurant_id, event_date, {", ".join(cols)}) VALUES (%s, %s, {", ".join(["%s"] * len(cols))})',
                                [(*k, *[v[c] for c in cols]) for k, v in res['new']])
            cur.executemany(f'UPDATE weather_events SET {", ".join(c + " = %s" for c in cols)} WHERE restaurant_id = %s AND event_date = %s',
                            [(*[v[c] for c in cols], *k) for k, v in res['update']])
    refresh_data_notification()
    return {'inserted': len(res['new']), 'updated': len(res['update']), 'skipped': res['skipped'], 'invalid': res['invalid']}


def model_info():
    try:
        tm = engine.trained_model()
    except Exception:
        return {'name': None, 'file': engine.MODEL_FILE, 'missing': True}
    metrics = {}
    try:
        df = pd.read_csv(Config.REPORTS_DIR / 'metrics.csv')
        metrics = {(r.model, r.split): float(r.wMAPE) for r in df.itertuples()}
    except (OSError, ValueError):
        pass
    best, naive = metrics.get((tm.model_name, 'test')), metrics.get(('SeasonalNaive_7', 'test'))
    return {'name': tm.model_name, 'file': engine.MODEL_FILE, 'trained_until': tm.trained_until,
            'test_range': f'{Config.TEST_START[8:]}/{Config.TEST_START[5:7]}–{Config.TEST_END[8:]}/{Config.TEST_END[5:7]}/{Config.TEST_END[:4]}',
            'wmape': round(best * 100, 1) if best else None, 'naive': round(naive * 100, 1) if naive else None,
            'gain': round((naive - best) / naive * 100, 1) if best and naive else None}


def store_runs(config=None):
    config, day = config or SystemConfig.get(), plans.service_date_of(config or SystemConfig.get())
    managers = {p.store_id: p.user for p in Profile.objects.filter(role=Role.MANAGER, user__is_active=True).select_related('user')}
    rows = []
    for store in Store.objects.all():
        inv = plans.latest_saved_inventory(store, config.operating_date)
        plan = plans.working_plan(store, day)
        mgr = managers.get(store.pk)
        if plan:
            label = {'pending': 'Chờ duyệt', 'approved': 'Đã duyệt'}[plan.status]
        elif not mgr:
            label = 'Chưa gán quản lý'
        elif not inv:
            label = 'Chưa có kiểm kho'
        else:
            label = 'Chưa chạy'
        rank = {'Chờ duyệt': 0, 'Chưa chạy': 1, 'Chưa gán quản lý': 2, 'Chưa có kiểm kho': 3, 'Đã duyệt': 4}[label]
        rows.append({'store': store, 'inventory': inv, 'plan': plan, 'label': label, 'manager': mgr, 'rank': rank,
                     'locked': plans.is_locked(plan, config)})
    return sorted(rows, key=lambda r: (r['rank'], r['store'].pk))


def store_series(store, config=None, days=14):
    config = config or SystemConfig.get()
    sales = (DailySale.objects.filter(restaurant=store, sale_date__lte=config.operating_date,
                                      sale_date__gt=config.operating_date - pd.Timedelta(days=days).to_pytimedelta())
             .values('sale_date').annotate(t=Sum('quantity')).order_by('sale_date'))
    actual = [(r['sale_date'], r['t']) for r in sales]
    plan = plans.working_plan(store, plans.service_date_of(config))
    forecast = None
    if plan:
        forecast = (plan.service_date, round(sum(l.forecast_qty for l in plan.lines.all()) * (1 + plan.adjustment_pct / 100)))
    return {'actual': actual, 'forecast': forecast}


def run_store(store, user, config=None):
    config = config or SystemConfig.get()
    return plans.create_plan(store, plans.service_date_of(config), user, config)


def run_all(user, config=None):
    config, summary = config or SystemConfig.get(), {'done': [], 'skipped': {}}
    for store in Store.objects.all():
        try:
            run_store(store, user, config)
            summary['done'].append(store.pk)
        except plans.PlanError as exc:
            summary['skipped'][store.pk] = exc.code
    return summary


def stores_overview(config=None):
    config = config or SystemConfig.get()
    managers = {p.store_id: p.user for p in Profile.objects.filter(role=Role.MANAGER, user__is_active=True).select_related('user')}
    stats = {r['restaurant']: r for r in DailySale.objects.filter(sale_date__year=config.operating_date.year, sale_date__lte=config.operating_date)
             .values('restaurant').annotate(s=Sum('quantity'), d=Count('sale_date', distinct=True), items=Count('product', distinct=True))}
    rows = []
    for st in Store.objects.all():
        x = stats.get(st.pk)
        mgr = managers.get(st.pk)
        rows.append({'store': st, 'items': x['items'] if x else 0, 'avg': round(x['s'] / x['d']) if x else 0,
                     'manager': (mgr.first_name or mgr.username) if mgr else None})
    return sorted(rows, key=lambda r: (r['manager'] is not None, r['store'].pk))


def _parse_city(text):
    m = re.fullmatch(r'\s*(.+?)\s*,\s*([A-Za-z]{2})\s*', text or '')
    if not m:
        raise AdminError('invalid', 'Thành phố nhập theo dạng "Tên thành phố, ST" (ví dụ Chicago, IL).')
    return m.group(1), m.group(2).upper()


@transaction.atomic
def save_store(code, name, city_text, manager_username=None, creating=False):
    code, name = (code or '').strip().upper(), (name or '').strip()
    if not code or not name or not (city_text or '').strip():
        raise AdminError('missing', 'Thiếu mã, tên hoặc thành phố · Hoàn thành các trường bắt buộc.')
    if not re.fullmatch(r'[A-Z0-9]{2,10}', code):
        raise AdminError('invalid', 'Mã cửa hàng gồm 2–10 chữ cái hoặc số.')
    city, state = _parse_city(city_text)
    exists = Store.objects.filter(pk=code).exists()
    if creating and exists:
        raise AdminError('duplicate', f'Mã cửa hàng {code} đã tồn tại.')
    if not creating and not exists:
        raise AdminError('not_found', 'Không tìm thấy cửa hàng.')
    Store.objects.update_or_create(pk=code, defaults={'restaurant_name': name, 'city': city, 'state': state})
    replaced = None
    if manager_username is not None and not creating:
        replaced = assign_manager(Store.objects.get(pk=code), manager_username)
    return Store.objects.get(pk=code), replaced


@transaction.atomic
def assign_manager(store, manager_label):
    current = Profile.objects.filter(role=Role.MANAGER, store=store).select_related('user')
    if manager_label in (None, '', 'Chưa gán'):
        current.update(store=None)
        return None
    target = Profile.objects.filter(role=Role.MANAGER, user__is_active=True).select_related('user') \
        .filter(user__first_name=manager_label).first() or Profile.objects.filter(role=Role.MANAGER, user__username=manager_label).first()
    if not target:
        raise AdminError('invalid', 'Không tìm thấy quản lý.')
    replaced = [p.user.first_name or p.user.username for p in current.exclude(pk=target.pk)]
    current.exclude(pk=target.pk).update(store=None)
    target.store = store
    target.save(update_fields=['store'])
    return replaced[0] if replaced else None


USERNAME_RE = re.compile(r'[a-z0-9._-]{3,30}')
ROLE_BY_LABEL = {label: value for value, label in Role.choices}


def _temp_password():
    return secrets.token_urlsafe(9)


def active_admin_count(excluding=None):
    qs = Profile.objects.filter(role=Role.ADMIN, user__is_active=True)
    return qs.exclude(user=excluding).count() if excluding else qs.count()


@transaction.atomic
def save_account(original, name, username, role_label, scope):
    name, username = (name or '').strip(), (username or '').strip().lower()
    role = ROLE_BY_LABEL.get(role_label)
    if not name or not username or not role or not scope:
        raise AdminError('missing', 'Thông tin tài khoản chưa hợp lệ · Kiểm tra các trường bắt buộc và phạm vi theo vai trò.')
    if not USERNAME_RE.fullmatch(username):
        raise AdminError('invalid', 'Tên đăng nhập gồm 3–30 ký tự: chữ thường, số, dấu . _ -')
    store = None
    if role == Role.ADMIN:
        if scope != 'Toàn hệ thống':
            raise AdminError('scope', 'Quản trị viên có phạm vi Toàn hệ thống.')
    else:
        store = Store.objects.filter(pk=scope.split(' · ')[0]).first()
        if not store:
            raise AdminError('scope', 'Quản lý và nhân viên phải thuộc một cửa hàng.')
    user = User.objects.filter(username=original).first() if original else None
    if original and not user:
        raise AdminError('not_found', 'Không tìm thấy tài khoản.')
    if User.objects.filter(username=username).exclude(pk=user.pk if user else None).exists():
        raise AdminError('duplicate', f'Tên đăng nhập {username} đã tồn tại.')
    if role == Role.MANAGER:
        other = Profile.objects.filter(role=Role.MANAGER, store=store, user__is_active=True).exclude(user=user).select_related('user').first()
        if other:
            raise AdminError('manager_conflict', f'{store.pk} đã có quản lý {other.user.first_name or other.user.username}.')
    temp = None
    if user:
        was_admin = hasattr(user, 'profile') and user.profile.role == Role.ADMIN
        if was_admin and role != Role.ADMIN and active_admin_count(excluding=user) == 0:
            raise AdminError('last_admin', 'Không thể đổi vai trò của quản trị viên cuối cùng.')
        user.username, user.first_name = username, name
    else:
        temp = _temp_password()
        user = User(username=username, first_name=name)
        user.set_password(temp)
    user.is_staff = user.is_superuser = role == Role.ADMIN
    user.save()
    Profile.objects.update_or_create(user=user, defaults={'role': role, 'store': store})
    return user, temp


@transaction.atomic
def set_active(username, actor, active):
    user = User.objects.filter(username=username).first()
    if not user:
        raise AdminError('not_found', 'Không tìm thấy tài khoản.')
    if not active:
        if user == actor:
            raise AdminError('self', 'Không thể vô hiệu hóa chính tài khoản đang đăng nhập.')
        if hasattr(user, 'profile') and user.profile.role == Role.ADMIN and active_admin_count(excluding=user) == 0:
            raise AdminError('last_admin', 'Không thể vô hiệu hóa quản trị viên cuối cùng.')
    user.is_active = active
    user.save(update_fields=['is_active'])
    return user


def reset_password(username):
    user = User.objects.filter(username=username, is_active=True).first()
    if not user:
        raise AdminError('not_found', 'Không tìm thấy tài khoản đang hoạt động.')
    temp = _temp_password()
    user.set_password(temp)
    user.save(update_fields=['password'])
    Notification.objects.filter(kind=Notification.Kind.DATA, role=Role.ADMIN, title=f'Yêu cầu cấp lại mật khẩu: {username}').delete()
    return user, temp


CHOICES = {'service_level': {'90%': 90, '95%': 95, '99%': 99},
           'prep_deadline': ('09:00', '10:00', '11:00'), 'inventory_reminder': ('20:00', '21:00', '22:00')}
TOGGLES = ('alert_red', 'alert_yellow', 'auto_plan_after_inventory', 'managers_can_run')


def save_config(data):
    cfg = SystemConfig.get()
    level = CHOICES['service_level'].get(str(data.get('service_level')).split(' ')[0])
    if level is None:
        raise AdminError('invalid', 'Mức an toàn phải là 90%, 95% hoặc 99%.')
    for field in ('prep_deadline', 'inventory_reminder'):
        if data.get(field) not in CHOICES[field]:
            raise AdminError('invalid', f'Giá trị {field} không hợp lệ.')
    if data.get('operating_date'):
        try:
            day = date.fromisoformat(str(data['operating_date']))
        except ValueError:
            raise AdminError('invalid', 'Ngày vận hành không hợp lệ.')
        first, last = plans.forecast_range()
        if not (first - timedelta(days=1) <= day <= last - timedelta(days=1)):
            raise AdminError('invalid', f'Ngày vận hành chỉ nhận từ {first - timedelta(days=1):%d/%m/%Y} đến {last - timedelta(days=1):%d/%m/%Y} '
                                        f'(ngày dự báo {first:%d/%m/%Y} – {last:%d/%m/%Y}).')
        cfg.operating_date = day
    cfg.service_level = level
    cfg.prep_deadline = datetime.strptime(data['prep_deadline'], '%H:%M').time()
    cfg.inventory_reminder = datetime.strptime(data['inventory_reminder'], '%H:%M').time()
    for t in TOGGLES:
        if t in data:
            setattr(cfg, t, bool(data[t]))
    cfg.save()
    return cfg
