

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forecast', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemconfig',
            name='inventory_reminder',
            field=models.TimeField(default=datetime.time(21, 0)),
        ),
        migrations.AlterField(
            model_name='systemconfig',
            name='prep_deadline',
            field=models.TimeField(default=datetime.time(10, 0)),
        ),
    ]
