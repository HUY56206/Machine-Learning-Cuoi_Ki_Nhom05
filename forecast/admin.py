"""Django Admin: cửa hàng, cấu hình hệ thống (theo mô tả nghiệp vụ QTV-4, QTV-5) và dữ liệu vận hành."""
from django.contrib import admin

from forecast.models import (InventoryCount, Notification, PrepPlan, Product, Profile, Store, SystemConfig)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('restaurant_id', 'restaurant_name', 'city', 'state')
    search_fields = ('restaurant_id', 'restaurant_name', 'city')


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    """Chỉ một dòng cấu hình; chỗ duy nhất đổi ngày vận hành và bật/tắt bắt buộc duyệt."""
    list_display = ('operating_date', 'service_level', 'require_approval', 'prep_deadline', 'inventory_reminder')

    def has_add_permission(self, request):
        return not SystemConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'store')
    list_filter = ('role',)


admin.site.register([Product, InventoryCount, PrepPlan, Notification])
