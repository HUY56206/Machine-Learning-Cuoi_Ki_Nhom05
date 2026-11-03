"""Mô hình dữ liệu của web.

Hai nhóm bảng cùng nằm trong MySQL `qsr_db`:
  - Bảng do pipeline ML tạo (Database/qsr_schema.sql): khai báo managed=False, Django chỉ đọc/ghi, không migrate.
  - Bảng của ứng dụng web (hồ sơ, kiểm kho, danh sách chuẩn bị, thông báo, cấu hình): do migration tạo.
"""
import datetime

from django.conf import settings
from django.db import models


# ====================================================================== bảng của pipeline ML
class Store(models.Model):
    restaurant_id = models.CharField(max_length=10, primary_key=True)
    restaurant_name = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=2)

    class Meta:
        managed = False
        db_table = 'stores'
        ordering = ['restaurant_id']

    def __str__(self):
        return f'{self.restaurant_id} · {self.restaurant_name}'


class Product(models.Model):
    menu_item_id = models.CharField(max_length=10, primary_key=True)
    menu_item_name = models.CharField(max_length=100)
    category = models.CharField(max_length=30)
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'products'
        ordering = ['menu_item_id']

    def __str__(self):
        return self.menu_item_name


class DailySale(models.Model):
    sale_id = models.IntegerField(primary_key=True)
    sale_date = models.DateField()
    restaurant = models.ForeignKey(Store, models.DO_NOTHING, db_column='restaurant_id', db_constraint=False)
    product = models.ForeignKey(Product, models.DO_NOTHING, db_column='menu_item_id', db_constraint=False)
    quantity = models.IntegerField()
    quantity_raw = models.IntegerField(null=True)
    is_imputed = models.BooleanField(default=False)
    is_outlier = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'daily_sales'


class WeatherEvent(models.Model):
    pk = models.CompositePrimaryKey('restaurant', 'event_date')
    restaurant = models.ForeignKey(Store, models.DO_NOTHING, db_column='restaurant_id', db_constraint=False)
    event_date = models.DateField()
    avg_temp_f = models.DecimalField(max_digits=5, decimal_places=1)
    precip_inches = models.DecimalField(max_digits=5, decimal_places=2)
    precip_type = models.CharField(max_length=10)
    is_holiday = models.BooleanField(default=False)
    holiday_name = models.CharField(max_length=60, null=True)
    is_special_event = models.BooleanField(default=False)
    special_event_name = models.CharField(max_length=60, null=True)

    class Meta:
        managed = False
        db_table = 'weather_events'


class Promotion(models.Model):
    promotion_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey(Store, models.DO_NOTHING, db_column='restaurant_id', db_constraint=False)
    product = models.ForeignKey(Product, models.DO_NOTHING, db_column='menu_item_id', db_constraint=False)
    promo_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'promotions'


class Forecast(models.Model):
    """Bảng `forecasts` do QSRInventory.saveForecasts ghi; web dùng để lưu dự báo thô theo ngày."""
    forecast_id = models.AutoField(primary_key=True)
    forecast_date = models.DateField()
    restaurant = models.ForeignKey(Store, models.DO_NOTHING, db_column='restaurant_id', db_constraint=False)
    product = models.ForeignKey(Product, models.DO_NOTHING, db_column='menu_item_id', db_constraint=False)
    predicted_qty = models.DecimalField(max_digits=8, decimal_places=2)
    safety_stock = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    current_stock = models.IntegerField(null=True)
    recommended_order = models.IntegerField(null=True)
    model_name = models.CharField(max_length=30)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'forecasts'


# ====================================================================== bảng của web
class Role(models.TextChoices):
    MANAGER = 'manager', 'Quản lý cửa hàng'
    STAFF = 'staff', 'Nhân viên bếp/kho'
    ADMIN = 'admin', 'Quản trị viên'


class Profile(models.Model):
    """Mở rộng auth.User: vai trò, cửa hàng phụ trách và tùy chọn thông báo."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=Role.choices)
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                              db_constraint=False, help_text='Để trống với quản trị viên (toàn hệ thống).')
    notify_new_plan = models.BooleanField(default=True)
    remind_inventory = models.BooleanField(default=True)
    weekly_email = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class SystemConfig(models.Model):
    """Cấu hình hệ thống – chỉ một dòng (pk=1)."""
    SERVICE_LEVELS = {90: 1.28, 95: 1.65, 99: 2.33}

    operating_date = models.DateField(help_text='Ngày vận hành hiện tại (demo: 30/10/2025). Dự báo cho ngày kế tiếp.')
    service_level = models.PositiveSmallIntegerField(default=95)
    alert_red = models.BooleanField(default=True)
    alert_yellow = models.BooleanField(default=True)
    require_approval = models.BooleanField(default=True, help_text='Bắt buộc quản lý duyệt trước khi gửi bếp.')
    prep_deadline = models.TimeField(default=datetime.time(10, 0))
    inventory_reminder = models.TimeField(default=datetime.time(21, 0))
    auto_plan_after_inventory = models.BooleanField(default=True)
    managers_can_run = models.BooleanField(default=True)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'operating_date': datetime.date(2025, 10, 30)})
        return obj

    @property
    def z(self):
        return self.SERVICE_LEVELS.get(self.service_level, 1.65)


class InventoryCount(models.Model):
    """Một lần kiểm kho. Bản nháp (draft) mỗi cửa hàng/ngày chỉ có một; mỗi lần lưu tạo thêm bản saved."""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Đã lưu nháp'
        SAVED = 'saved', 'Đã lưu'

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='+', db_constraint=False)
    count_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['store', 'count_date', 'status'])]


class InventoryItem(models.Model):
    count = models.ForeignKey(InventoryCount, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+', db_constraint=False)
    quantity = models.IntegerField(null=True, blank=True, help_text='Số lượng còn lại; null = chưa nhập.')
    prev_quantity = models.IntegerField(null=True, blank=True, help_text='Tồn kỳ trước.')

    class Meta:
        unique_together = [('count', 'product')]

    @property
    def needs_review(self):
        return self.quantity is not None and self.prev_quantity and self.quantity < self.prev_quantity * 0.25


class PrepPlan(models.Model):
    """Đề xuất chuẩn bị hàng cho một ngày phục vụ. Chạy dự báo lại tạo phiên bản mới (version + 1)."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ duyệt'
        APPROVED = 'approved', 'Đã duyệt'
        SUPERSEDED = 'superseded', 'Đã thay thế'

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='+', db_constraint=False)
    service_date = models.DateField()
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    model_name = models.CharField(max_length=30, blank=True)
    inventory_count = models.ForeignKey(InventoryCount, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    adjustment_pct = models.IntegerField(default=0)
    adjustment_reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True, help_text='Quản lý mở lại danh sách đã duyệt để chạy lại.')

    class Meta:
        ordering = ['-version']
        unique_together = [('store', 'service_date', 'version')]


class PrepLine(models.Model):
    class Level(models.TextChoices):
        SHORT = 'short', 'Thiếu hàng'
        TOPUP = 'topup', 'Cần bổ sung'
        OK = 'ok', 'Đủ hàng'

    plan = models.ForeignKey(PrepPlan, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='+', db_constraint=False)
    forecast_qty = models.IntegerField()
    baseline_qty = models.IntegerField(default=0, help_text='"Bình thường": trung bình 7 ngày trước.')
    safety_stock = models.IntegerField()
    current_stock = models.IntegerField()
    need_qty = models.IntegerField(help_text='Dự báo + tồn an toàn − tồn hiện tại (≥ 0).')
    applied_qty = models.IntegerField(help_text='Số lượng áp dụng (quản lý có thể chỉnh).')
    level = models.CharField(max_length=6, choices=Level.choices)
    done_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('plan', 'product')]
        ordering = ['-applied_qty']


class Notification(models.Model):
    class Kind(models.TextChoices):
        SHORTAGE = 'shortage', 'Thiếu hàng'
        INVENTORY = 'inventory', 'Kiểm kho'
        EVENT = 'event', 'Sự kiện'
        PREP = 'prep', 'Chuẩn bị hàng'
        DATA = 'data', 'Dữ liệu'
        PLAN = 'plan', 'Đề xuất mới'
        REMINDER = 'reminder', 'Nhắc kiểm kho'

    kind = models.CharField(max_length=10, choices=Kind.choices)
    role = models.CharField(max_length=10, choices=Role.choices, help_text='Vai trò nhận thông báo.')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, related_name='+', db_constraint=False)
    title = models.CharField(max_length=120)
    detail = models.CharField(max_length=255, blank=True)
    link = models.CharField(max_length=40, blank=True, help_text='Tên url (namespace forecast).')
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='+')

    class Meta:
        ordering = ['-created_at']
