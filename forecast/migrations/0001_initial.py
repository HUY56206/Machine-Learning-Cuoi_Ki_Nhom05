

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DailySale',
            fields=[
                ('sale_id', models.IntegerField(primary_key=True, serialize=False)),
                ('sale_date', models.DateField()),
                ('quantity', models.IntegerField()),
                ('quantity_raw', models.IntegerField(null=True)),
                ('is_imputed', models.BooleanField(default=False)),
                ('is_outlier', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'daily_sales',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Forecast',
            fields=[
                ('forecast_id', models.AutoField(primary_key=True, serialize=False)),
                ('forecast_date', models.DateField()),
                ('predicted_qty', models.DecimalField(decimal_places=2, max_digits=8)),
                ('safety_stock', models.DecimalField(decimal_places=2, max_digits=8, null=True)),
                ('current_stock', models.IntegerField(null=True)),
                ('recommended_order', models.IntegerField(null=True)),
                ('model_name', models.CharField(max_length=30)),
                ('created_at', models.DateTimeField()),
            ],
            options={
                'db_table': 'forecasts',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('menu_item_id', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('menu_item_name', models.CharField(max_length=100)),
                ('category', models.CharField(max_length=30)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=6)),
            ],
            options={
                'db_table': 'products',
                'ordering': ['menu_item_id'],
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Promotion',
            fields=[
                ('promotion_id', models.AutoField(primary_key=True, serialize=False)),
                ('promo_date', models.DateField()),
            ],
            options={
                'db_table': 'promotions',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Store',
            fields=[
                ('restaurant_id', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('restaurant_name', models.CharField(max_length=100)),
                ('city', models.CharField(max_length=50)),
                ('state', models.CharField(max_length=2)),
            ],
            options={
                'db_table': 'stores',
                'ordering': ['restaurant_id'],
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='WeatherEvent',
            fields=[
                ('pk', models.CompositePrimaryKey('restaurant', 'event_date', blank=True, editable=False, primary_key=True, serialize=False)),
                ('event_date', models.DateField()),
                ('avg_temp_f', models.DecimalField(decimal_places=1, max_digits=5)),
                ('precip_inches', models.DecimalField(decimal_places=2, max_digits=5)),
                ('precip_type', models.CharField(max_length=10)),
                ('is_holiday', models.BooleanField(default=False)),
                ('holiday_name', models.CharField(max_length=60, null=True)),
                ('is_special_event', models.BooleanField(default=False)),
                ('special_event_name', models.CharField(max_length=60, null=True)),
            ],
            options={
                'db_table': 'weather_events',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='SystemConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operating_date', models.DateField(help_text='Ngày vận hành hiện tại (demo: 30/10/2025). Dự báo cho ngày kế tiếp.')),
                ('service_level', models.PositiveSmallIntegerField(default=95)),
                ('alert_red', models.BooleanField(default=True)),
                ('alert_yellow', models.BooleanField(default=True)),
                ('require_approval', models.BooleanField(default=True, help_text='Bắt buộc quản lý duyệt trước khi gửi bếp.')),
                ('prep_deadline', models.TimeField(default='10:00')),
                ('inventory_reminder', models.TimeField(default='21:00')),
                ('auto_plan_after_inventory', models.BooleanField(default=True)),
                ('managers_can_run', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='InventoryCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_date', models.DateField()),
                ('status', models.CharField(choices=[('draft', 'Đã lưu nháp'), ('saved', 'Đã lưu')], default='draft', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('store', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='forecast.store')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(blank=True, help_text='Số lượng còn lại; null = chưa nhập.', null=True)),
                ('prev_quantity', models.IntegerField(blank=True, help_text='Tồn kỳ trước.', null=True)),
                ('count', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='forecast.inventorycount')),
                ('product', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='forecast.product')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('shortage', 'Thiếu hàng'), ('inventory', 'Kiểm kho'), ('event', 'Sự kiện'), ('prep', 'Chuẩn bị hàng'), ('data', 'Dữ liệu')], max_length=10)),
                ('role', models.CharField(choices=[('manager', 'Quản lý cửa hàng'), ('staff', 'Nhân viên bếp/kho'), ('admin', 'Quản trị viên')], help_text='Vai trò nhận thông báo.', max_length=10)),
                ('title', models.CharField(max_length=120)),
                ('detail', models.CharField(blank=True, max_length=255)),
                ('link', models.CharField(blank=True, help_text='Tên url (namespace forecast).', max_length=40)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_by', models.ManyToManyField(blank=True, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('store', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='forecast.store')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PrepPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_date', models.DateField()),
                ('version', models.PositiveIntegerField(default=1)),
                ('status', models.CharField(choices=[('pending', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('superseded', 'Đã thay thế')], default='pending', max_length=12)),
                ('model_name', models.CharField(blank=True, max_length=30)),
                ('adjustment_pct', models.IntegerField(default=0)),
                ('adjustment_reason', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('reopened_at', models.DateTimeField(blank=True, help_text='Quản lý mở lại danh sách đã duyệt để chạy lại.', null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('inventory_count', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='forecast.inventorycount')),
                ('store', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='forecast.store')),
            ],
            options={
                'ordering': ['-version'],
            },
        ),
        migrations.CreateModel(
            name='PrepLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('forecast_qty', models.IntegerField()),
                ('baseline_qty', models.IntegerField(default=0, help_text='"Bình thường": trung bình 7 ngày trước.')),
                ('safety_stock', models.IntegerField()),
                ('current_stock', models.IntegerField()),
                ('need_qty', models.IntegerField(help_text='Dự báo + tồn an toàn − tồn hiện tại (≥ 0).')),
                ('applied_qty', models.IntegerField(help_text='Số lượng áp dụng (quản lý có thể chỉnh).')),
                ('level', models.CharField(choices=[('short', 'Thiếu hàng'), ('topup', 'Cần bổ sung'), ('ok', 'Đủ hàng')], max_length=6)),
                ('done_at', models.DateTimeField(blank=True, null=True)),
                ('done_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='forecast.product')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='forecast.prepplan')),
            ],
            options={
                'ordering': ['-applied_qty'],
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('manager', 'Quản lý cửa hàng'), ('staff', 'Nhân viên bếp/kho'), ('admin', 'Quản trị viên')], max_length=10)),
                ('notify_new_plan', models.BooleanField(default=True)),
                ('remind_inventory', models.BooleanField(default=True)),
                ('weekly_email', models.BooleanField(default=False)),
                ('store', models.ForeignKey(blank=True, db_constraint=False, help_text='Để trống với quản trị viên (toàn hệ thống).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='forecast.store')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='inventorycount',
            index=models.Index(fields=['store', 'count_date', 'status'], name='forecast_in_store_i_968604_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='inventoryitem',
            unique_together={('count', 'product')},
        ),
        migrations.AlterUniqueTogether(
            name='prepplan',
            unique_together={('store', 'service_date', 'version')},
        ),
        migrations.AlterUniqueTogether(
            name='prepline',
            unique_together={('plan', 'product')},
        ),
    ]
