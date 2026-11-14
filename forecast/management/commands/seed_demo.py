import random
from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone

from forecast.models import (DailySale, InventoryCount, InventoryItem, Notification, PrepPlan, Product, Profile, Role, Store,
                             SystemConfig)
from forecast.services import adminops, plans

ACCOUNTS = [

    ('lan.r01', 'vjtSKDEP%96', 'Quản lý R01', Role.MANAGER, 'R01'),
    ('khanh.r01', 'UTxmJhkV!40', 'Nhân viên R01', Role.STAFF, 'R01'),
    ('trang.r02', '7AXSTTwM!86', 'Quản lý R02', Role.MANAGER, 'R02'),
    ('nam.r02', 'ukYcs7PR#17', 'Nhân viên R02', Role.STAFF, 'R02'),
    ('yen.r03', 'jSS6k2tD%62', 'Quản lý R03', Role.MANAGER, 'R03'),
    ('tuan.r03', '52NVaJcu$51', 'Nhân viên R03', Role.STAFF, 'R03'),
    ('chi.r04', 'QabyMfhC%65', 'Quản lý R04', Role.MANAGER, 'R04'),
    ('kien.r04', '4W7xd3t3$66', 'Nhân viên R04', Role.STAFF, 'R04'),
    ('huong.r05', 'nS722UFE#91', 'Quản lý R05', Role.MANAGER, 'R05'),
    ('thao.r05', 'y6FHPP7w$63', 'Nhân viên R05', Role.STAFF, 'R05'),
    ('loan.r06', 'b9nNE2TG!21', 'Quản lý R06', Role.MANAGER, 'R06'),
    ('hanh.r06', '8bAfs2nm@74', 'Nhân viên R06', Role.STAFF, 'R06'),
    ('khoa.r07', 'TY6k93Dz@85', 'Quản lý R07', Role.MANAGER, 'R07'),
    ('phong.r07', 'bt5sb78Q%43', 'Nhân viên R07', Role.STAFF, 'R07'),
    ('nhung.r08', 'psRm3uZr@29', 'Quản lý R08', Role.MANAGER, 'R08'),
    ('tam.r08', 'DXekXKb8!65', 'Nhân viên R08', Role.STAFF, 'R08'),
    ('son.r09', 'aRgV4ayV$67', 'Quản lý R09', Role.MANAGER, 'R09'),
    ('duc.r09', 'fKu4bMgf#54', 'Nhân viên R09', Role.STAFF, 'R09'),
    ('quan.r10', 'Mw7U87Ge#21', 'Quản lý R10', Role.MANAGER, 'R10'),
    ('quyen.r10', 'Nz2HD8fK!81', 'Nhân viên R10', Role.STAFF, 'R10'),
    ('vy.r11', 'C2hR7eTs%61', 'Quản lý R11', Role.MANAGER, 'R11'),
    ('hoa.r11', 'MJz2VcCf!60', 'Nhân viên R11', Role.STAFF, 'R11'),
    ('an.r12', 'fkjJCdLb!26', 'Quản lý R12', Role.MANAGER, 'R12'),
    ('phuc.r12', 'MuMMFa2D$35', 'Nhân viên R12', Role.STAFF, 'R12'),
    ('nhi.r13', 'uHGZqCKK@96', 'Quản lý R13', Role.MANAGER, 'R13'),
    ('thu.r13', 'WNAXGwxB@36', 'Nhân viên R13', Role.STAFF, 'R13'),
    ('lam.r14', 'He7SdLBX@31', 'Quản lý R14', Role.MANAGER, 'R14'),
    ('minh.r14', 'Uqr4qRF9%80', 'Nhân viên R14', Role.STAFF, 'R14'),
    ('long.r15', 'wWthbmTZ%24', 'Quản lý R15', Role.MANAGER, 'R15'),
    ('ha.r15', 'Lf7h7KrC#37', 'Nhân viên R15', Role.STAFF, 'R15'),
    ('admin', 'VaHhXjMc!75', 'Quản trị viên', Role.ADMIN, None),
]

COUNT_HISTORY = [(1, 14, 10), (1, 21, 45), (0, 14, 0)]


class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu cho web QSR Forecast.'

    def add_arguments(self, parser):
        parser.add_argument('--no-plan', action='store_true', help='Không chạy dự báo để tạo đề xuất chờ duyệt.')
        parser.add_argument('--reset', action='store_true',
                            help='Xóa mọi đề xuất, kiểm kho, thông báo và đưa cấu hình về mặc định (dữ liệu bán hàng giữ nguyên).')

    def handle(self, *args, **opts):
        if opts['reset']:
            self._reset()
        config = SystemConfig.get()
        self.stdout.write(f'Ngày vận hành: {config.operating_date:%d/%m/%Y}')

        for username, password, name, role, store_id in ACCOUNTS:
            user, _ = User.objects.update_or_create(username=username, defaults={
                'first_name': name, 'is_active': True, 'is_staff': role == Role.ADMIN, 'is_superuser': role == Role.ADMIN})
            user.set_password(password)
            user.save()
            Profile.objects.update_or_create(user=user, defaults={
                'role': role, 'store': Store.objects.get(pk=store_id) if store_id else None})
        self.stdout.write(self.style.SUCCESS(f'Đã tạo {len(ACCOUNTS)} tài khoản (xem bảng trong Kich_Ban.md).'))


        staff = {s: u for u, _, _, r, s in ACCOUNTS if r == Role.STAFF}
        for store_id in ('R01', 'R02'):
            self._seed_inventory(Store.objects.get(pk=store_id), User.objects.get(username=staff[store_id]), config)

        if not opts['no_plan']:
            store = Store.objects.get(pk='R01')
            day = plans.service_date_of(config)
            if plans.working_plan(store, day) is None:
                plan = plans.create_plan(store, day, User.objects.get(username=next(u for u, _, _, r, st in ACCOUNTS if r == Role.MANAGER and st == 'R01')), config)
                self.stdout.write(self.style.SUCCESS(f'Đề xuất R01 {day:%d/%m/%Y}: {plan.lines.count()} món, chờ duyệt'))
        self.stdout.write(f'Dòng thiếu số lượng: {adminops.refresh_data_notification(config):,}')
        self.stdout.write(self.style.SUCCESS('Xong.'))

    def _reset(self):
        plans_n = PrepPlan.objects.count()
        counts_n = InventoryCount.objects.count()
        PrepPlan.objects.all().delete()
        InventoryCount.objects.all().delete()
        Notification.objects.all().delete()
        SystemConfig.objects.filter(pk=1).delete()
        SystemConfig.get()
        self.stdout.write(self.style.WARNING(f'Đã xóa {plans_n} đề xuất, {counts_n} lần kiểm kho và mọi thông báo; cấu hình về mặc định.'))

    def _seed_inventory(self, store, user, config):
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
