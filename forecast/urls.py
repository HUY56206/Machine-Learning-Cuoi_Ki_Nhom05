from django.urls import path

from . import api, api_admin, views

app_name = 'forecast'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('no-access/', views.no_access, name='no_access'),
    # Quản lý cửa hàng
    path('dashboard/', views.dashboard, name='dashboard'),
    path('prep/', views.prep, name='prep'),
    path('prep/export/', views.prep_export, name='prep_export'),
    path('forecast/', views.forecast, name='forecast'),
    path('report/', views.report, name='report'),
    # Quản trị viên
    path('admin-data/', views.data, name='data'),
    path('admin-model/', views.model, name='model'),
    path('admin-stores/', views.stores, name='stores'),
    path('admin-accounts/', views.accounts, name='accounts'),
    path('admin-config/', views.config, name='config'),
    # Nhân viên bếp/kho
    path('staff/prep/', views.staff_prep, name='staff_prep'),
    path('staff/inventory/', views.inventory, name='inventory'),
    # API
    path('api/forecast/run/', api.run_forecast, name='api_run_forecast'),
    path('api/plan/<int:plan_id>/', api.plan_detail, name='api_plan_detail'),
    path('api/plan/<int:plan_id>/adjust/', api.adjust_plan, name='api_adjust_plan'),
    path('api/plan/<int:plan_id>/approve/', api.approve_plan, name='api_approve_plan'),
    path('api/plan/<int:plan_id>/reopen/', api.reopen_plan, name='api_reopen_plan'),
    path('api/line/<int:line_id>/qty/', api.adjust_line, name='api_adjust_line'),
    path('api/line/<int:line_id>/reason/', api.line_reason, name='api_line_reason'),
    path('api/line/<int:line_id>/done/', api.line_done, name='api_line_done'),
    path('api/inventory/save/', api.save_inventory, name='api_save_inventory'),
    path('api/notifications/', api.notifications, name='api_notifications'),
    path('api/notifications/read/', api.read_notifications, name='api_read_notifications'),
    path('api/profile/password/', api.change_password, name='api_change_password'),
    path('api/profile/prefs/', api.save_prefs, name='api_save_prefs'),
    path('api/password-reset/', api.password_reset_request, name='api_password_reset'),
    # API quản trị viên
    path('api/admin/data/missing/', api_admin.data_missing, name='api_admin_missing'),
    path('api/admin/data/import/', api_admin.data_import, name='api_admin_import'),
    path('api/admin/forecast/run/', api_admin.run_store, name='api_admin_run'),
    path('api/admin/forecast/run-all/', api_admin.run_all, name='api_admin_run_all'),
    path('api/admin/explain/', api_admin.explain_model, name='api_admin_explain'),
    path('api/admin/stores/save/', api_admin.save_store, name='api_admin_save_store'),
    path('api/admin/accounts/save/', api_admin.save_account, name='api_admin_save_account'),
    path('api/admin/accounts/disable/', api_admin.disable_account, name='api_admin_disable_account'),
    path('api/admin/accounts/reset-password/', api_admin.reset_password, name='api_admin_reset_password'),
    path('api/admin/config/save/', api_admin.save_config, name='api_admin_save_config'),
]
