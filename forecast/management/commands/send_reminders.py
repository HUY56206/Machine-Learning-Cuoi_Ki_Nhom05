from django.core.management.base import BaseCommand

from forecast.services import plans


class Command(BaseCommand):
    help = 'Tạo thông báo nhắc kiểm kho cho các cửa hàng chưa lưu kiểm kho ngày vận hành.'

    def handle(self, *args, **opts):
        self.stdout.write(f'Đã nhắc {plans.send_inventory_reminders()} cửa hàng.')
