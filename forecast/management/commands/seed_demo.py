"""Tạo dữ liệu mẫu để chạy thử web: cấu hình, tài khoản theo thiết kế, lịch sử kiểm kho và một đề xuất chờ duyệt.

    python manage.py seed_demo            # mật khẩu mặc định in ra màn hình
    python manage.py seed_demo --password "MatKhauCuaBan" --no-plan
Chạy lại được nhiều lần (idempotent).
"""
import random
from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone

from forecast.models import (DailySale, InventoryCount, InventoryItem, PrepPlan, Product, Profile, Role, Store, SystemConfig)
from forecast.services import adminops, plans

DEMO_PASSWORD = 'Qsr@2025!'
USERS = [
    # username, tên hiển thị, vai trò, cửa hàng
    ('lan.r01', 'Quản lý R01', Role.MANAGER, 'R01'),
    ('minh.r01', 'Nhân viên R01', Role.STAFF, 'R01'),
    ('hung.r02', 'Quản lý R02', Role.MANAGER, 'R02'),
    ('mai.r02', 'Nhân viên R02', Role.STAFF, 'R02'),
    ('admin', 'Quản trị viên', Role.ADMIN, None),
]
# (số ngày trước ngày vận hành, giờ, phút)
COUNT_HISTORY = [(1, 14, 10), (1, 21, 45), (0, 14, 0)]


class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu cho web QSR Forecast.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEMO_PASSWORD)
        parser.add_argument('--no-plan', action='store_true', help='Không chạy dự báo để tạo đề xuất chờ duyệt.')

    def handle(self, *args, **opts):
        config = SystemConfig.get()
        self.stdout.write(f'Ngày vận hành: {config.operating_date:%d/%m/%Y}')

        for username, name, role, store_id in USERS:
            user, _ = User.objects.update_or_create(username=username, defaults={
                'first_name': name, 'is_active': True, 'is_staff': role == Role.ADMIN, 'is_superuser': role == Role.ADMIN})
            user.set_password(opts['password'])
            user.save()
            Profile.objects.update_or_create(user=user, defaults={
                'role': role, 'store': Store.objects.get(pk=store_id) if store_id else None})
        self.stdout.write(self.style.SUCCESS(f'Tài khoản: {", ".join(u[0] for u in USERS)} | mật khẩu: {opts["password"]}'))

        for store_id, staff_name in (('R01', 'minh.r01'), ('R02', 'mai.r02')):
            self._seed_inventory(Store.objects.get(pk=store_id), User.objects.get(username=staff_name), config)

        if not opts['no_plan']:
            store = Store.objects.get(pk='R01')
            day = plans.service_date_of(config)
            if plans.working_plan(store, day) is None:
                plan = plans.create_plan(store, day, User.objects.get(username='lan.r01'), config)
                self.stdout.write(self.style.SUCCESS(f'Đề xuất R01 {day:%d/%m/%Y}: {plan.lines.count()} món, chờ duyệt'))
        self.stdout.write(f'Dòng thiếu số lượng: {adminops.refresh_data_notification(config):,}')
        self.stdout.write(self.style.SUCCESS('Xong.'))

    def _seed_inventory(self, store, user, config):
        """Tồn mô phỏng = 0,2–1,1 lần bán trung bình 7 ngày (dataset không có tồn kho thực tế)."""
        products = list(Product.objects.all())
        rng = random.Random(f'{store.pk}-{config.operating_date}')
        for days_ago, hour, minute in COUNT_HISTORY:
            day = config.operating_date - timedelta(days=days_ago)
            stamp = timezone.make_aware(datetime.combine(day, time(hour, minute)))
            if InventoryCount.objects.filter(store=store, count_date=day, created_at=stamp).exists():
                continue
            avg = dict(DailySale.objects.filter(restaurant=store, sale_date__gt=day - timedelta(days=7), sale_date__lte=day)
                       .values_list('product_id').annotate(a=Avg('quantity')))
            count = InventoryCount.objects.create(store=store, count_date=day, status=InventoryCount.Status.SAVED, user=user)
            InventoryCount.objects.filter(pk=count.pk).update(created_at=stamp, updated_at=stamp)
            InventoryItem.objects.bulk_create([
                InventoryItem(count=count, product=p, quantity=round(float(avg.get(p.pk, 20)) * rng.uniform(0.2, 1.1)))
                for p in products])
        self.stdout.write(f'Kiểm kho {store.pk}: {InventoryCount.objects.filter(store=store).count()} lần')
