"""API JSON của quản trị viên. Cùng quy ước lỗi với forecast/api.py: {ok: False, error, message}."""
import logging

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from forecast.api import body, fail
from forecast.models import Product, Role, Store
from forecast.permissions import api_role_required
from forecast.services import adminops, explain, plans
from forecast.services.engine import NoForecastData
from forecast.services.adminops import AdminError
from forecast.views import parse_date

ADMIN = Role.ADMIN
SERVER_ERROR = 'Không thể chạy dự báo do lỗi hệ thống · Thử lại sau ít phút.'
logger = logging.getLogger(__name__)
RUN_MESSAGES = {'approved': 'Đã duyệt – quản lý cần mở lại danh sách trước khi chạy lại.',
                'no_inventory': 'Chưa có kiểm kho để tính lượng cần chuẩn bị.', 'no_data': 'Không có dữ liệu đầu vào cho ngày đã chọn.'}


def admin_error(exc, status=400):
    return fail(exc.code, str(exc), status)


# ----------------------------------------------------------------------------- dữ liệu
@require_GET
@api_role_required(ADMIN)
def data_missing(request):
    start, end = parse_date(request.GET.get('from')), parse_date(request.GET.get('to'))
    if not start or not end:
        return fail('invalid', 'Kỳ dữ liệu không hợp lệ.')
    return JsonResponse({'ok': True, **adminops.missing_summary(start, end), 'rows': adminops.missing_rows(start, end)})


@require_POST
@api_role_required(ADMIN)
def data_import(request):
    """multipart: group, mode, file, confirm ('1' = ghi thật; mặc định chỉ kiểm tra và xem trước)."""
    f = request.FILES.get('file')
    if not f:
        return fail('no_file', 'Chưa chọn tệp hợp lệ · Chọn tệp CSV hoặc Excel để tiếp tục.')
    group, mode = request.POST.get('group', ''), request.POST.get('mode', '')
    try:
        if request.POST.get('confirm') == '1':
            return JsonResponse({'ok': True, 'result': adminops.commit_import(group, mode, f.name, f.read())})
        res = adminops.analyse_import(group, mode, f.name, f.read())
    except AdminError as exc:
        return admin_error(exc)
    return JsonResponse({'ok': True, 'preview': {
        'file': res['file'], 'columns_ok': res['columns_ok'], 'missing_columns': res['missing_columns'], 'total': res['total'],
        'new': len(res['new']), 'update': len(res['update']), 'skipped': res['skipped'], 'invalid': res['invalid'],
        'errors': res['errors'], 'sample': res['sample'], 'columns': res['columns']}})


# ----------------------------------------------------------------------------- chạy dự báo
@require_POST
@api_role_required(ADMIN)
def run_store(request):
    store = Store.objects.filter(pk=body(request).get('store')).first()
    if not store:
        return fail('not_found', 'Không tìm thấy cửa hàng.', 404)
    try:
        plan = adminops.run_store(store, request.user)
    except plans.PlanError as exc:
        return fail(exc.code, RUN_MESSAGES.get(exc.code, str(exc)), 409 if exc.code == 'approved' else 400)
    except Exception:
        logger.exception('Admin chạy dự báo lỗi: %s', store.pk)
        return fail('server_error', SERVER_ERROR, 500)
    from forecast.api import plan_json
    return JsonResponse({'ok': True, 'plan': plan_json(plan), 'store_name': f'{store.pk} · {store.restaurant_name}'})


@require_POST
@api_role_required(ADMIN)
def run_all(request):
    try:
        return JsonResponse({'ok': True, **adminops.run_all(request.user)})
    except Exception:
        logger.exception('Admin chạy dự báo toàn hệ thống lỗi')
        return fail('server_error', SERVER_ERROR, 500)


# ----------------------------------------------------------------------------- giải thích mô hình (SHAP)
@require_GET
@api_role_required(ADMIN)
def explain_model(request):
    """Quản trị viên: mức ảnh hưởng của từng yếu tố tới dự báo của một cửa hàng (mọi cửa hàng), có thể chọn thêm một món."""
    store = Store.objects.filter(pk=request.GET.get('store')).first()
    if not store:
        return fail('not_found', 'Không tìm thấy cửa hàng.', 404)
    first, last = plans.forecast_range()
    day = parse_date(request.GET.get('date'), plans.service_date_of())
    if not (first <= day <= last):
        return fail('out_of_range', f'Ngày chỉ nhận từ {first:%d/%m/%Y} đến {last:%d/%m/%Y}.')
    product = request.GET.get('product') or None
    if product and not Product.objects.filter(pk=product).exists():
        return fail('not_found', 'Không tìm thấy món.', 404)
    try:
        data = explain.admin_view(store.pk, day, product)
    except NoForecastData:
        return fail('no_data', 'Không có dữ liệu đầu vào cho ngày đã chọn.')
    except Exception:
        logger.exception('Admin SHAP lỗi: %s %s', store.pk, day)
        return fail('server_error', 'Không thể tính mức ảnh hưởng do lỗi hệ thống · Thử lại sau ít phút.', 500)
    return JsonResponse({'ok': True, 'store': store.pk, 'date': day.isoformat(), **data})


# ----------------------------------------------------------------------------- cửa hàng
@require_POST
@api_role_required(ADMIN)
def save_store(request):
    d = body(request)
    try:
        store, replaced = adminops.save_store(d.get('code'), d.get('name'), d.get('city'), d.get('manager'), creating=bool(d.get('creating')))
    except AdminError as exc:
        return admin_error(exc)
    return JsonResponse({'ok': True, 'store': store.pk, 'replaced': replaced})


# ----------------------------------------------------------------------------- tài khoản
@require_POST
@api_role_required(ADMIN)
def save_account(request):
    d = body(request)
    try:
        user, temp = adminops.save_account(d.get('original'), d.get('name'), d.get('username'), d.get('role'), d.get('scope'))
    except AdminError as exc:
        return admin_error(exc, 409 if exc.code in ('duplicate', 'manager_conflict', 'last_admin') else 400)
    return JsonResponse({'ok': True, 'username': user.username, 'temp_password': temp})


@require_POST
@api_role_required(ADMIN)
def disable_account(request):
    try:
        adminops.set_active(body(request).get('username'), request.user, False)
    except AdminError as exc:
        return admin_error(exc, 409)
    return JsonResponse({'ok': True})


@require_POST
@api_role_required(ADMIN)
def reset_password(request):
    try:
        user, temp = adminops.reset_password(body(request).get('username'))
    except AdminError as exc:
        return admin_error(exc, 404)
    return JsonResponse({'ok': True, 'username': user.username, 'temp_password': temp})


# ----------------------------------------------------------------------------- cấu hình
@require_POST
@api_role_required(ADMIN)
def save_config(request):
    try:
        adminops.save_config(body(request))
    except AdminError as exc:
        return admin_error(exc)
    from django.utils import timezone
    return JsonResponse({'ok': True, 'at': timezone.localtime().strftime('%d/%m/%Y %H:%M')})
