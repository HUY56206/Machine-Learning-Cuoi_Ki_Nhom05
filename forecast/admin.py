from django.contrib import admin

from forecast.models import (InventoryCount, Notification, PrepPlan, Product, Profile, Store, SystemConfig)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('restaurant_id', 'restaurant_name', 'city', 'state')
    search_fields = ('restaurant_id', 'restaurant_name', 'city')


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
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
