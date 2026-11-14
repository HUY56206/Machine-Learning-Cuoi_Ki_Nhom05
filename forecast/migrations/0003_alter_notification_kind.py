

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecast', '0002_alter_systemconfig_inventory_reminder_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='kind',
            field=models.CharField(choices=[('shortage', 'Thiếu hàng'), ('inventory', 'Kiểm kho'), ('event', 'Sự kiện'), ('prep', 'Chuẩn bị hàng'), ('data', 'Dữ liệu'), ('plan', 'Đề xuất mới'), ('reminder', 'Nhắc kiểm kho')], max_length=10),
        ),
    ]
