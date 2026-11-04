"""Nghiệp vụ đề xuất chuẩn bị hàng & kiểm kho (không phụ thuộc HTTP, dễ kiểm thử)."""
import math
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from forecast.models import (InventoryCount, InventoryItem, Notification, PrepLine, PrepPlan, Product, Profile, Role,
                             Store, SystemConfig, WeatherEvent)
from forecast.services import engine
from forecast.services.notifications import notify
from Utils import Config


class PlanError(Exception):
    """Lỗi nghiệp vụ có mã để giao diện chọn đúng popup."""

    def __init__(self, code, message=''):
        super().__init__(message or code)
        self.code = code


def forecast_range():
    """Khoảng ngày được phép dự báo trên web: từ ngày đầu tập validation đến hết tập test (theo Utils/Config.py).
    Các ngày thuộc tập train mô hình đã học nên không cho chọn (kết quả sẽ đẹp giả tạo)."""
    return date.fromisoformat(Config.VAL_START), date.fromisoformat(Config.TEST_END)


# ----------------------------------------------------------------------------- truy vấn trạng thái
def service_date_of(config=None):
    """Ngày phục vụ = ngày vận hành + 1 (dự báo ngày mai)."""
    config = config or SystemConfig.get()
    return config.operating_date + timedelta(days=1)


def latest_saved_inventory(store, on_or_before):
    return (InventoryCount.objects.filter(store=store, status=InventoryCount.Status.SAVED, count_date__lte=on_or_before)
            .order_by('-count_date', '-created_at').first())


def working_plan(store, service_date):
    """Phiên bản đề xuất mới nhất (đang làm việc) của quản lý."""
    return PrepPlan.objects.filter(store=store, service_date=service_date).exclude(
        status=PrepPlan.Status.SUPERSEDED).order_by('-version').first()


def kitchen_plan(store, service_date, config=None):
    """Danh sách bếp nhìn thấy. Cần duyệt: bản đã duyệt gần nhất (bản mới chỉ gửi bếp sau khi duyệt lại).
    Không cần duyệt (cấu hình): bản mới nhất, gửi bếp ngay khi tính xong."""
    config = config or SystemConfig.get()
    qs = PrepPlan.objects.filter(store=store, service_date=service_date)
    qs = qs.filter(status=PrepPlan.Status.APPROVED) if config.require_approval else qs.exclude(status=PrepPlan.Status.SUPERSEDED)
    return qs.order_by('-version').first()


def is_locked(plan, config=None):
    """Đã duyệt và chưa mở lại -> không cho chạy lại dự báo (chỉ áp dụng khi bắt buộc quản lý duyệt)."""
    config = config or SystemConfig.get()
    return bool(config.require_approval and plan and plan.status == PrepPlan.Status.APPROVED and plan.reopened_at is None)


def actionable_lines(plan):
    """Các món bếp phải làm: số lượng áp dụng > 0."""
    return plan.lines.filter(applied_qty__gt=0)


def is_complete(plan):
    """Hoàn thành: đã duyệt/gửi bếp và mọi món cần làm đều được đánh dấu xong."""
    lines = actionable_lines(plan)
    return plan.status == PrepPlan.Status.APPROVED and lines.exists() and not lines.filter(done_at=None).exists()


# ----------------------------------------------------------------------------- tính toán
def level_of(need, current, safety):
    if need <= 0:
        return PrepLine.Level.OK
    return PrepLine.Level.SHORT if current < safety else PrepLine.Level.TOPUP


def compute_line(forecast, safety, current, pct=0):
    """Dự báo đã điều chỉnh + tồn an toàn − tồn hiện tại (không âm, làm tròn lên)."""
    adjusted = forecast * (1 + pct / 100)
    need = max(0, math.ceil(adjusted + safety - current))
    return need, level_of(need, current, safety)


def recalc_plan(plan):
    """Áp tỷ lệ điều chỉnh của đề xuất lên mọi dòng (giữ nguyên số quản lý chỉnh tay nếu khác tính toán)."""
    lines = list(plan.lines.all())
    for ln in lines:
        need, level = compute_line(ln.forecast_qty, ln.safety_stock, ln.current_stock, plan.adjustment_pct)
        ln.need_qty, ln.applied_qty, ln.level = need, need, level
    PrepLine.objects.bulk_update(lines, ['need_qty', 'applied_qty', 'level'])


# ----------------------------------------------------------------------------- chạy dự báo
@transaction.atomic
def create_plan(store, service_date, user, config=None):
    config = config or SystemConfig.get()
    first, last = forecast_range()
    if service_date < first:
        raise PlanError('train_data', f'Ngày {service_date:%d/%m/%Y} thuộc dữ liệu huấn luyện của mô hình, '
                                      f'không dự báo. Chọn ngày từ {first:%d/%m/%Y} đến {last:%d/%m/%Y}.')
    # Ngày sau khoảng này (hoặc không có dữ liệu đầu vào trong DB) sẽ báo no_data từ engine.
    current = working_plan(store, service_date)
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
    version = (PrepPlan.objects.filter(store=store, service_date=service_date).order_by('-version')
               .values_list('version', flat=True).first() or 0) + 1
    if current:                                   # bản chờ duyệt cũ bị thay thế
        PrepPlan.objects.filter(store=store, service_date=service_date,
                                status=PrepPlan.Status.PENDING).update(status=PrepPlan.Status.SUPERSEDED)

    plan = PrepPlan.objects.create(store=store, service_date=service_date, version=version,
                                   model_name=df['model_name'].iloc[0], inventory_count=inv, created_by=user)
    lines, raw_stock, raw_need = [], [], []
    for r in df.itertuples(index=False):
        fc, safe = round(r.predicted_qty), math.ceil(r.safety_stock)
        cur = stock.get(r.menu_item_id, 0)
        need, level = compute_line(fc, safe, cur)
        lines.append(PrepLine(plan=plan, product=products[r.menu_item_id], forecast_qty=fc,
                              baseline_qty=round(r.baseline_qty) if r.baseline_qty == r.baseline_qty else 0,
                              safety_stock=safe, current_stock=cur, need_qty=need, applied_qty=need, level=level))
        raw_stock.append(cur)
        raw_need.append(need)
    PrepLine.objects.bulk_create(lines)

    try:                                          # ghi bảng forecasts cũ; lỗi ở đây không làm hỏng đề xuất
        engine.save_raw_forecasts(df, raw_stock, raw_need)
    except Exception:
        pass

    if config.require_approval:
        notify(Notification.Kind.PLAN, Role.STAFF, store, 'Danh sách chuẩn bị đang chờ duyệt',
                f'Ngày phục vụ: {service_date:%d/%m/%Y}', 'staff_prep')
    else:                                                     # không cần duyệt: gửi bếp ngay
        _publish(plan, user)
    short = sum(1 for l in lines if l.level == PrepLine.Level.SHORT)
    if config.alert_red:
        notify(Notification.Kind.SHORTAGE, Role.MANAGER, store, f'Thiếu hàng: {short} món',
                f'{"Chờ duyệt" if config.require_approval else "Đã gửi bếp"} · {store.pk} · {timezone.localtime():%d/%m/%Y %H:%M}', 'prep')
    event = WeatherEvent.objects.filter(restaurant=store, event_date=service_date).first()
    if event and (event.is_special_event or event.is_holiday):
        notify(Notification.Kind.EVENT, Role.MANAGER, store, f'Sự kiện: {event.special_event_name or event.holiday_name}',
                f'Ngày phục vụ: {service_date:%d/%m/%Y}', 'forecast')
    return plan


# ----------------------------------------------------------------------------- điều chỉnh / duyệt
@transaction.atomic
def set_adjustment(plan, pct, reason):
    if plan.status != PrepPlan.Status.PENDING:
        raise PlanError('not_pending', 'Chỉ điều chỉnh được đề xuất đang chờ duyệt.')
    if not -30 <= pct <= 30:
        raise PlanError('invalid', 'Tỷ lệ điều chỉnh nằm trong khoảng −30% … +30%.')
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
    """Gửi danh sách cho bếp: bản đã duyệt cũ bị thay thế, bếp nhận thông báo."""
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
    if done and is_complete(plan):                            # bước 6: quản lý nhận thông báo hoàn thành
        notify(Notification.Kind.PREP, Role.MANAGER, plan.store, 'Chuẩn bị hàng đã hoàn tất',
                f'{user.first_name or user.username} · {timezone.localtime():%d/%m/%Y %H:%M}', 'prep')
    return line


def send_inventory_reminders(now=None, config=None):
    """Đến giờ nhắc mà cửa hàng chưa lưu kiểm kho ngày vận hành -> nhắc nhân viên (chạy bằng cron)."""
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


# ----------------------------------------------------------------------------- kiểm kho
def inventory_progress(items):
    """Trả về (đã nhập, cần xem lại, chưa nhập) cho danh sách InventoryItem hoặc dict số liệu."""
    entered = sum(1 for i in items if i.quantity is not None)
    review = sum(1 for i in items if i.needs_review)
    return entered, review, len(items) - entered


@transaction.atomic
def save_inventory(store, count_date, user, quantities, draft, config=None):
    """quantities: {menu_item_id: int|None}. Bản nháp ghi đè; lưu chính thức yêu cầu đủ 50 món."""
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
                plan = None                       # đã duyệt / thiếu dữ liệu: giữ nguyên, báo ở giao diện
    return count, plan
