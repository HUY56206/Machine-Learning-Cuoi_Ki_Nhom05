import datetime
import json
from unittest import mock

import pandas as pd
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase

from forecast.models import (DailySale, Forecast, InventoryCount, Notification, PrepLine, PrepPlan, Product, Profile,
                             Promotion, Role, Store, SystemConfig, WeatherEvent)
from forecast.services import engine, explain, plans

UNMANAGED = [Store, Product, DailySale, WeatherEvent, Promotion, Forecast]
OP_DATE = datetime.date(2025, 10, 30)
SERVICE = datetime.date(2025, 10, 31)


def fake_forecast(store_id, service_date, z=1.65):
    return pd.DataFrame({
        'menu_item_id': ['M01', 'M02', 'M03'], 'predicted_qty': [100.4, 50.0, 5.0],
        'safety_stock': [19.2, 10.0, 2.0], 'baseline_qty': [80.0, 40.0, 4.0], 'model_name': 'catboost'})


class Base(TestCase):
    @classmethod
    def setUpClass(cls):
        with connection.schema_editor() as editor:
            for m in UNMANAGED:
                editor.create_model(m)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as editor:
            for m in reversed(UNMANAGED):
                editor.delete_model(m)

    def setUp(self):
        self.r01 = Store.objects.create(restaurant_id='R01', restaurant_name='Downtown', city='Chicago', state='IL')
        self.r02 = Store.objects.create(restaurant_id='R02', restaurant_name='Wrigley', city='Chicago', state='IL')
        for pid, name, cat in [('M01', 'Classic Cheeseburger', 'Burgers'), ('M02', 'French Fries Regular', 'Sides'),
                               ('M03', 'Soft Drink Regular', 'Drinks')]:
            Product.objects.create(menu_item_id=pid, menu_item_name=name, category=cat, unit_price=5)
        self.config = SystemConfig.get()
        self.users = {}
        for name, role, store in [('mgr1', Role.MANAGER, self.r01), ('stf1', Role.STAFF, self.r01),
                                  ('mgr2', Role.MANAGER, self.r02), ('adm', Role.ADMIN, None)]:
            u = User.objects.create_user(name, password='pw-12345-abc', first_name=name)
            Profile.objects.create(user=u, role=role, store=store)
            self.users[name] = u

    def count(self, store, qty, day=OP_DATE):
        c = InventoryCount.objects.create(store=store, count_date=day, status=InventoryCount.Status.SAVED, user=self.users['stf1'])
        for pid, q in qty.items():
            c.items.create(product_id=pid, quantity=q)
        return c

    def post(self, client, url, data=None):
        return client.post(url, json.dumps(data or {}), content_type='application/json')


class PlanLogicTests(Base):
    def test_compute_line_levels(self):
        self.assertEqual(plans.compute_line(100, 20, 5), (115, PrepLine.Level.SHORT))
        self.assertEqual(plans.compute_line(100, 20, 30), (90, PrepLine.Level.TOPUP))
        self.assertEqual(plans.compute_line(10, 2, 50), (0, PrepLine.Level.OK))
        self.assertEqual(plans.compute_line(100, 20, 0, pct=10), (130, PrepLine.Level.SHORT))

    @mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_create_plan_needs_inventory(self, *_):
        with self.assertRaises(plans.PlanError) as ctx:
            plans.create_plan(self.r01, SERVICE, self.users['mgr1'])
        self.assertEqual(ctx.exception.code, 'no_inventory')

    @mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_create_plan_lines(self, *_):
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        plan = plans.create_plan(self.r01, SERVICE, self.users['mgr1'])
        lines = {l.product_id: l for l in plan.lines.all()}
        self.assertEqual((lines['M01'].need_qty, lines['M01'].level), (115, 'short'))
        self.assertEqual((lines['M02'].need_qty, lines['M02'].level), (30, 'topup'))
        self.assertEqual((lines['M03'].need_qty, lines['M03'].level), (0, 'ok'))
        self.assertEqual(plan.status, PrepPlan.Status.PENDING)
        self.assertEqual(Notification.objects.filter(kind="shortage", store=self.r01).count(), 1)

    @mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_approve_lock_reopen_versions(self, *_):
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        mgr = self.users['mgr1']
        v1 = plans.create_plan(self.r01, SERVICE, mgr)
        plans.approve(v1, mgr)
        self.assertTrue(plans.is_locked(plans.working_plan(self.r01, SERVICE)))
        with self.assertRaises(plans.PlanError) as ctx:
            plans.create_plan(self.r01, SERVICE, mgr)
        self.assertEqual(ctx.exception.code, 'approved')

        plans.reopen(v1)
        v2 = plans.create_plan(self.r01, SERVICE, mgr)
        self.assertEqual(v2.version, 2)
        self.assertEqual(plans.kitchen_plan(self.r01, SERVICE).pk, v1.pk)
        plans.approve(v2, mgr)
        self.assertEqual(plans.kitchen_plan(self.r01, SERVICE).pk, v2.pk)
        v1.refresh_from_db()
        self.assertEqual(v1.status, PrepPlan.Status.SUPERSEDED)

    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_raw_forecasts_saved_only_after_commit(self, *_):
        self.count(self.r01, {'M01': 5, 'M02': 5, 'M03': 5})
        with mock.patch.object(engine, 'save_raw_forecasts', return_value=3) as saver:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                plans.create_plan(self.r01, SERVICE, self.users['mgr1'])
            self.assertEqual(saver.call_count, 0)
            for cb in callbacks:
                cb()
            self.assertEqual(saver.call_count, 1)

    @mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_adjustment_and_line_edit(self, *_):
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        plan = plans.create_plan(self.r01, SERVICE, self.users['mgr1'])
        with self.assertRaises(plans.PlanError):
            plans.set_adjustment(plan, 15, '')
        with self.assertRaises(plans.PlanError):
            plans.set_adjustment(plan, 50, 'Sự kiện')
        with self.assertRaises(plans.PlanError):
            plans.set_adjustment(plan, 10, 'Sự kiện')
        plans.set_adjustment(plan, 15, 'Sự kiện tại cửa hàng')
        m01 = plan.lines.get(product_id='M01')
        self.assertEqual(m01.need_qty, 130)
        plans.set_line_qty(m01, 140)
        m01.refresh_from_db()
        self.assertEqual((m01.need_qty, m01.applied_qty), (130, 140))
        plans.approve(plan, self.users['mgr1'])
        with self.assertRaises(plans.PlanError):
            plans.set_line_qty(m01, 1)

    @mock.patch.object(engine, 'forecast_store', side_effect=engine.NoForecastData('x'))
    def test_no_data(self, *_):
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        with self.assertRaises(plans.PlanError) as ctx:
            plans.create_plan(self.r01, SERVICE, self.users['mgr1'])
        self.assertEqual(ctx.exception.code, 'no_data')


class InventoryTests(Base):
    def test_draft_then_final_requires_all_items(self):
        stf = self.users['stf1']
        plans.save_inventory(self.r01, OP_DATE, stf, {'M01': 3, 'M02': None}, draft=True)
        plans.save_inventory(self.r01, OP_DATE, stf, {'M01': 4}, draft=True)
        self.assertEqual(InventoryCount.objects.filter(status='draft').count(), 1)
        with self.assertRaises(plans.PlanError) as ctx:
            plans.save_inventory(self.r01, OP_DATE, stf, {'M01': 3, 'M02': 4}, draft=False)
        self.assertEqual(ctx.exception.code, 'incomplete')
        with self.assertRaises(plans.PlanError):
            plans.save_inventory(self.r01, OP_DATE, stf, {'M01': -1, 'M02': 1, 'M03': 1}, draft=True)
        with self.assertRaises(plans.PlanError):
            plans.save_inventory(self.r01, OP_DATE, stf, {'ZZ': 1}, draft=True)

    @mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_final_save_creates_plan_and_prev_quantity(self, *_):
        stf = self.users['stf1']
        self.count(self.r01, {'M01': 40, 'M02': 40, 'M03': 40}, day=OP_DATE - datetime.timedelta(days=1))
        count, plan = plans.save_inventory(self.r01, OP_DATE, stf, {'M01': 5, 'M02': 30, 'M03': 100}, draft=False)
        self.assertIsNotNone(plan)
        self.assertEqual(count.items.get(product_id='M01').prev_quantity, 40)
        self.assertTrue(count.items.get(product_id='M01').needs_review)
        self.assertFalse(count.items.get(product_id='M02').needs_review)
        self.assertTrue(Notification.objects.filter(kind='inventory').exists())

    def test_final_save_skips_plan_when_locked(self):
        stf, mgr = self.users['stf1'], self.users['mgr1']
        with mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast), \
                mock.patch.object(engine, 'save_raw_forecasts', return_value=3):
            self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
            plans.approve(plans.create_plan(self.r01, SERVICE, mgr), mgr)
            _, plan = plans.save_inventory(self.r01, OP_DATE, stf, {'M01': 1, 'M02': 1, 'M03': 1}, draft=False)
        self.assertIsNone(plan)


class PermissionTests(Base):
    def login(self, name):
        self.client.force_login(self.users[name])

    def test_anonymous_redirects_and_api_401(self):
        r = self.client.get('/prep/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])
        self.assertEqual(self.post(self.client, '/api/forecast/run/').status_code, 401)

    def test_role_guards(self):
        self.login('stf1')
        self.assertEqual(self.client.get('/prep/').status_code, 403)
        self.assertEqual(self.client.get('/admin-data/').status_code, 403)
        self.assertEqual(self.post(self.client, '/api/forecast/run/').status_code, 403)
        self.login('mgr1')
        self.assertEqual(self.client.get('/staff/prep/').status_code, 403)
        self.assertEqual(self.post(self.client, '/api/inventory/save/', {}).status_code, 403)

    def test_home_redirects_by_role(self):
        for name, target in [('mgr1', '/dashboard/'), ('stf1', '/staff/prep/'), ('adm', '/admin-data/')]:
            self.login(name)
            self.assertEqual(self.client.get('/')['Location'], target)

    def test_login_json(self):
        bad = self.client.post('/login/', {'username': 'mgr1', 'password': 'sai'})
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post('/login/', {'username': 'mgr1', 'password': 'pw-12345-abc'})
        self.assertEqual(ok.json(), {'ok': True, 'next': '/dashboard/'})
        evil = self.client.post('/login/', {'username': 'mgr1', 'password': 'pw-12345-abc', 'next': 'https://evil.example/'})
        self.assertEqual(evil.json()['next'], '/dashboard/')

    @mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_cannot_touch_other_store_plan(self, *_):
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        plan = plans.create_plan(self.r01, SERVICE, self.users['mgr1'])
        self.login('mgr2')
        for action in ('approve', 'reopen', 'adjust'):
            self.assertEqual(self.post(self.client, f'/api/plan/{plan.pk}/{action}/', {'pct': 5, 'reason': 'x'}).status_code, 404)
        line = plan.lines.first()
        self.assertEqual(self.post(self.client, f'/api/line/{line.pk}/qty/', {'qty': 1}).status_code, 404)

    @mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_api_flow(self, *_):
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        self.login('mgr1')
        run = self.post(self.client, '/api/forecast/run/', {'date': '31/10/2025'}).json()
        self.assertTrue(run['ok'])
        pid = run['plan']['id']
        self.assertEqual(self.post(self.client, f'/api/plan/{pid}/adjust/', {'pct': 15, 'reason': ''}).json()['error'], 'reason_required')
        self.assertTrue(self.post(self.client, f'/api/plan/{pid}/approve/').json()['ok'])
        again = self.post(self.client, '/api/forecast/run/', {'date': '31/10/2025'})
        self.assertEqual((again.status_code, again.json()['error'], again.json()['plan_id']), (409, 'approved', pid))
        self.assertTrue(self.post(self.client, f'/api/plan/{pid}/reopen/').json()['ok'])
        self.assertTrue(self.post(self.client, '/api/forecast/run/', {'date': '31/10/2025'}).json()['ok'])

        self.login('stf1')
        line = PrepLine.objects.filter(plan_id=pid, level='short').first()
        self.assertTrue(self.post(self.client, f'/api/line/{line.pk}/done/').json()['ok'])
        line.refresh_from_db()
        self.assertIsNotNone(line.done_at)

    def test_manager_run_can_be_disabled(self):
        SystemConfig.objects.filter(pk=1).update(managers_can_run=False)
        self.login('mgr1')
        self.assertEqual(self.post(self.client, '/api/forecast/run/').status_code, 403)

    def test_password_change(self):
        self.login('mgr1')
        self.assertEqual(self.post(self.client, '/api/profile/password/', {'current': 'sai', 'new': 'Abcdef-123456', 'again': 'Abcdef-123456'}).json()['error'], 'wrong_password')
        self.assertEqual(self.post(self.client, '/api/profile/password/', {'current': 'pw-12345-abc', 'new': 'Abcdef-123456', 'again': 'khac'}).json()['error'], 'mismatch')
        self.assertEqual(self.post(self.client, '/api/profile/password/', {'current': 'pw-12345-abc', 'new': '123', 'again': '123'}).json()['error'], 'weak_password')
        self.assertTrue(self.post(self.client, '/api/profile/password/', {'current': 'pw-12345-abc', 'new': 'Abcdef-123456', 'again': 'Abcdef-123456'}).json()['ok'])
        self.assertTrue(User.objects.get(username='mgr1').check_password('Abcdef-123456'))


class Phase1LogicTests(Base):

    def setUp(self):
        super().setUp()
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        patch1 = mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
        patch2 = mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
        patch1.start(), patch2.start()
        self.addCleanup(patch1.stop), self.addCleanup(patch2.stop)
        self.mgr, self.stf = self.users['mgr1'], self.users['stf1']

    def test_any_date_can_be_forecast(self):
        for day in (SERVICE + datetime.timedelta(days=1), OP_DATE):
            self.assertEqual(plans.create_plan(self.r01, day, self.mgr).service_date, day)

    def test_training_dates_are_rejected(self):
        first, _ = plans.forecast_range()
        self.assertEqual(first, datetime.date(2025, 7, 1))
        for day in (first - datetime.timedelta(days=1), datetime.date(2025, 6, 25), datetime.date(2021, 3, 1)):
            with self.assertRaises(plans.PlanError) as ctx:
                plans.create_plan(self.r01, day, self.mgr)
            self.assertEqual(ctx.exception.code, 'train_data')
        self.assertEqual(plans.create_plan(self.r01, first, self.mgr).service_date, first)

    def test_date_without_input_data_reports_no_data(self):
        with mock.patch.object(engine, 'forecast_store', side_effect=engine.NoForecastData('x')):
            with self.assertRaises(plans.PlanError) as ctx:
                plans.create_plan(self.r01, SERVICE + datetime.timedelta(days=400), self.mgr)
        self.assertEqual(ctx.exception.code, 'no_data')

    def test_no_approval_required_sends_to_kitchen(self):
        SystemConfig.objects.filter(pk=1).update(require_approval=False)
        plan = plans.create_plan(self.r01, SERVICE, self.mgr)
        self.assertEqual(plan.status, PrepPlan.Status.APPROVED)
        self.assertEqual(plans.kitchen_plan(self.r01, SERVICE).pk, plan.pk)
        again = plans.create_plan(self.r01, SERVICE, self.mgr)
        self.assertEqual(plans.kitchen_plan(self.r01, SERVICE).pk, again.pk)

    def test_pending_plan_hidden_from_kitchen(self):
        plans.create_plan(self.r01, SERVICE, self.mgr)
        self.assertIsNone(plans.kitchen_plan(self.r01, SERVICE))

    def test_red_alert_off_skips_shortage_notification(self):
        SystemConfig.objects.filter(pk=1).update(alert_red=False)
        plans.create_plan(self.r01, SERVICE, self.mgr)
        self.assertFalse(Notification.objects.filter(kind='shortage').exists())

    def test_completion_notifies_manager(self):
        plan = plans.approve(plans.create_plan(self.r01, SERVICE, self.mgr), self.mgr)
        todo = list(plans.actionable_lines(plan))
        for line in todo[:-1]:
            plans.mark_done(line, self.stf)
        self.assertFalse(plans.is_complete(plan))
        plans.mark_done(todo[-1], self.stf)
        self.assertTrue(plans.is_complete(plan))
        self.assertTrue(Notification.objects.filter(role='manager', title='Chuẩn bị hàng đã hoàn tất').exists())

    def test_event_notification_and_prefs(self):
        WeatherEvent.objects.create(restaurant=self.r01, event_date=SERVICE, avg_temp_f=50, precip_inches=0, precip_type='None',
                                    is_special_event=True, special_event_name='Halloween')
        plans.create_plan(self.r01, SERVICE, self.mgr)
        from forecast.services.notifications import visible_for
        kinds = set(visible_for(self.mgr).values_list('kind', flat=True))
        self.assertTrue({'shortage', 'event'} <= kinds)
        Profile.objects.filter(user=self.mgr).update(notify_new_plan=False)
        self.mgr.refresh_from_db()
        self.assertNotIn('shortage', set(visible_for(User.objects.get(pk=self.mgr.pk)).values_list('kind', flat=True)))

    def test_inventory_reminder(self):
        InventoryCount.objects.all().delete()
        early = datetime.datetime(2025, 10, 30, 20, 0, tzinfo=datetime.timezone.utc).astimezone()
        late = early.replace(hour=22)
        self.assertEqual(plans.send_inventory_reminders(early.replace(hour=12)), 0)
        self.assertEqual(plans.send_inventory_reminders(late), 1)
        self.count(self.r01, {'M01': 1, 'M02': 1, 'M03': 1})
        self.assertEqual(plans.send_inventory_reminders(late), 0)

    def test_login_remember_and_throttle(self):
        ok = self.client.post('/login/', {'username': 'mgr1', 'password': 'pw-12345-abc'})
        self.assertTrue(ok.json()['ok'])
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        self.client.logout()
        self.client.post('/login/', {'username': 'mgr1', 'password': 'pw-12345-abc', 'remember': 'on'})
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.client.logout()
        for _ in range(5):
            self.client.post('/login/', {'username': 'stf1', 'password': 'sai'})
        locked = self.client.post('/login/', {'username': 'stf1', 'password': 'pw-12345-abc'})
        self.assertEqual((locked.status_code, locked.json()['error']), (429, 'locked'))

    def test_user_without_store_is_blocked(self):
        Profile.objects.filter(user=self.mgr).update(store=None)
        self.client.force_login(self.mgr)
        self.assertEqual(self.client.get('/dashboard/').status_code, 403)
        self.assertEqual(self.post(self.client, '/api/forecast/run/').status_code, 403)

    @mock.patch.object(explain, 'store_explanation', side_effect=RuntimeError('no model'))
    def test_reason_insights_endpoint(self, *_):
        plan = plans.create_plan(self.r01, SERVICE, self.mgr)
        DailySale.objects.create(sale_id=1, sale_date=SERVICE - datetime.timedelta(days=7), restaurant=self.r01,
                                 product_id='M01', quantity=70)
        self.client.force_login(self.mgr)
        data = self.client.get(f'/api/line/{plan.lines.get(product_id="M01").pk}/reason/').json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['similar'], [{'date': '24/10/2025', 'qty': 70}])
        self.assertIsNone(data['contrib'])
        self.client.force_login(self.users['mgr2'])
        self.assertEqual(self.client.get(f'/api/line/{plan.lines.first().pk}/reason/').status_code, 404)


class AdminOpsTests(Base):

    def setUp(self):
        super().setUp()
        from forecast.services import adminops
        self.ops = adminops
        self.adm = self.users['adm']


    def test_account_rules(self):
        ops = self.ops
        user, temp = ops.save_account('', 'Nhân viên mới', 'new.r01', 'Nhân viên bếp/kho', 'R01 · Downtown')
        self.assertTrue(temp and user.check_password(temp))
        self.assertEqual((user.profile.role, user.profile.store_id), ('staff', 'R01'))
        for args, code in [(('', 'X', 'new.r01', 'Nhân viên bếp/kho', 'R01 · D'), 'duplicate'),
                           (('', 'X', 'Bad Name', 'Nhân viên bếp/kho', 'R01 · D'), 'invalid'),
                           (('', 'X', 'abc.def', 'Quản lý cửa hàng', 'R01 · D'), 'manager_conflict'),
                           (('', 'X', 'abc.def', 'Quản lý cửa hàng', 'Toàn hệ thống'), 'scope'),
                           (('', 'X', 'abc.def', 'Quản trị viên', 'R01 · D'), 'scope'),
                           (('', '', 'abc.def', 'Quản trị viên', 'Toàn hệ thống'), 'missing')]:
            with self.assertRaises(ops.AdminError) as ctx:
                ops.save_account(*args)
            self.assertEqual(ctx.exception.code, code, args)
        ops.save_account('new.r01', 'Đổi tên', 'new.r01', 'Nhân viên bếp/kho', 'R02 · Wrigley')
        self.assertEqual(User.objects.get(username='new.r01').profile.store_id, 'R02')
        with self.assertRaises(ops.AdminError) as ctx:
            ops.save_account('adm', 'Admin', 'adm', 'Nhân viên bếp/kho', 'R02 · Wrigley')
        self.assertEqual(ctx.exception.code, 'last_admin')

    def test_disable_and_reset(self):
        ops = self.ops
        with self.assertRaises(ops.AdminError):
            ops.set_active('adm', self.adm, False)
        ops.set_active('stf1', self.adm, False)
        self.assertFalse(self.client.login(username='stf1', password='pw-12345-abc'))
        self.assertEqual(self.client.post('/login/', {'username': 'stf1', 'password': 'pw-12345-abc'}).status_code, 400)
        user, temp = ops.reset_password('mgr1')
        self.assertTrue(User.objects.get(username='mgr1').check_password(temp))
        with self.assertRaises(ops.AdminError):
            ops.reset_password('stf1')


    def test_store_save_and_assign_manager(self):
        ops = self.ops
        store, _ = ops.save_store('r03', 'Indy', 'Indianapolis, in', creating=True)
        self.assertEqual((store.pk, store.city, store.state), ('R03', 'Indianapolis', 'IN'))
        for args, code in [(('R03', 'x', 'y, IL', None, True), 'duplicate'), (('', 'x', 'y, IL'), 'missing'),
                           (('R04', 'x', 'Chicago', None, True), 'invalid')]:
            with self.assertRaises(ops.AdminError) as ctx:
                ops.save_store(*args)
            self.assertEqual(ctx.exception.code, code)

        replaced = ops.assign_manager(self.r02, 'mgr1')
        self.assertEqual(replaced, 'mgr2')
        self.assertEqual(Profile.objects.get(user__username='mgr1').store_id, 'R02')
        self.assertIsNone(Profile.objects.get(user__username='mgr2').store_id)
        ops.assign_manager(self.r02, 'Chưa gán')
        self.assertIsNone(Profile.objects.get(user__username='mgr1').store_id)


    def test_config_save(self):
        ops = self.ops
        ops.save_config({'service_level': '99% (z = 2,33)', 'prep_deadline': '09:00', 'inventory_reminder': '22:00',
                         'alert_red': False, 'require_approval': False})
        cfg = SystemConfig.get()
        self.assertEqual((cfg.service_level, cfg.z, str(cfg.prep_deadline)[:5], cfg.alert_red), (99, 2.33, '09:00', False))
        self.assertTrue(cfg.require_approval)
        for bad in ({'service_level': '80%', 'prep_deadline': '09:00', 'inventory_reminder': '22:00'},
                    {'service_level': '95%', 'prep_deadline': '12:00', 'inventory_reminder': '22:00'}):
            with self.assertRaises(ops.AdminError):
                ops.save_config(bad)

    def test_config_operating_date(self):
        import datetime as dt
        ops = self.ops
        base = {'service_level': '95%', 'prep_deadline': '09:00', 'inventory_reminder': '22:00'}
        ops.save_config({**base, 'operating_date': '2025-12-12'})
        self.assertEqual(plans.service_date_of(), dt.date(2025, 12, 13))
        for bad in ('2025-06-29', '2025-12-31', 'abc'):
            with self.assertRaises(ops.AdminError):
                ops.save_config({**base, 'operating_date': bad})
        self.assertEqual(SystemConfig.get().operating_date, dt.date(2025, 12, 12))


    def csv(self, text):
        return text.encode('utf-8')

    def test_import_sales_new_update_skip_invalid(self):
        ops = self.ops
        DailySale.objects.create(sale_id=1, sale_date=SERVICE, restaurant=self.r01, product_id='M01', quantity=10, quantity_raw=None, is_imputed=True)
        raw = self.csv('sale_date,restaurant_id,menu_item_id,quantity\n'
                       '2025-10-31,R01,M01,25\n'
                       '2025-10-31,R01,M02,30\n'
                       '31/10/2025,R02,M03,7\n'
                       '2025-10-31,R99,M01,5\n'
                       '2025-10-31,R01,M01,3\n'
                       '2025-10-31,R01,M03,-4\n')
        add = ops.analyse_import('Bán hàng hằng ngày', 'Thêm dữ liệu mới', 'a.csv', raw)
        self.assertEqual((len(add['new']), len(add['update']), add['skipped'], add['invalid']), (2, 0, 2, 2))
        upd = ops.analyse_import('Bán hàng hằng ngày', 'Cập nhật theo khóa', 'a.csv', raw)
        self.assertEqual((len(upd['new']), len(upd['update'])), (0, 1))
        res = ops.commit_import('Bán hàng hằng ngày', 'Thêm dữ liệu mới', 'a.csv', raw)
        self.assertEqual((res['inserted'], res['skipped']), (2, 2))
        self.assertEqual(DailySale.objects.count(), 3)
        self.assertEqual(DailySale.objects.get(restaurant_id='R01', product_id='M02').quantity, 30)
        ops.commit_import('Bán hàng hằng ngày', 'Cập nhật theo khóa', 'a.csv', raw)
        first = DailySale.objects.get(sale_id=1)
        self.assertEqual((first.quantity, first.quantity_raw, first.is_imputed), (25, 25, False))
        self.assertEqual(ops.missing_summary(SERVICE, SERVICE)['missing'], 0)

    def test_import_columns_and_errors(self):
        ops = self.ops
        bad = ops.analyse_import('Bán hàng hằng ngày', 'Thêm dữ liệu mới', 'a.csv', self.csv('sale_date,quantity\n2025-10-31,3\n'))
        self.assertEqual(bad['missing_columns'], ['restaurant_id', 'menu_item_id'])
        with self.assertRaises(ops.AdminError):
            ops.commit_import('Bán hàng hằng ngày', 'Thêm dữ liệu mới', 'a.csv', self.csv('sale_date,quantity\n2025-10-31,3\n'))
        with self.assertRaises(ops.AdminError):
            ops.analyse_import('Bán hàng hằng ngày', 'Thêm dữ liệu mới', 'a.txt', b'x')
        with self.assertRaises(ops.AdminError):
            ops.analyse_import('Nhóm lạ', 'Thêm dữ liệu mới', 'a.csv', b'x')

    def test_import_weather_and_holiday(self):
        ops = self.ops
        w = self.csv('event_date,restaurant_id,avg_temp_f,precip_type\n2025-10-31,R01,50.4,None\n2025-10-31,R02,40,Hail\n')
        res = ops.commit_import('Thời tiết', 'Thêm dữ liệu mới', 'w.csv', w)
        self.assertEqual((res['inserted'], res['invalid']), (1, 1))
        h = self.csv('event_date,restaurant_id,is_special_event,special_event_name\n2025-10-31,R01,1,Halloween\n2025-11-01,R01,1,X\n')
        res = ops.commit_import('Ngày lễ & sự kiện', 'Cập nhật theo khóa', 'h.csv', h)
        self.assertEqual((res['updated'], res['skipped']), (1, 1))
        ev = WeatherEvent.objects.get(restaurant_id='R01', event_date=SERVICE)
        self.assertEqual((ev.is_special_event, ev.special_event_name), (True, 'Halloween'))
        promo = self.csv('promo_date,restaurant_id,menu_item_id\n2025-10-31,R01,M01\n2025-10-31,R01,M01\n')
        self.assertEqual(ops.commit_import('Khuyến mãi', 'Thêm dữ liệu mới', 'p.csv', promo)['inserted'], 1)


    @mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
    @mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
    def test_run_all_skips_without_inventory_or_approved(self, *_):
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        out = self.ops.run_all(self.adm)
        self.assertEqual(out['done'], ['R01'])
        self.assertEqual(out['skipped'], {'R02': 'no_inventory'})
        plans.approve(plans.working_plan(self.r01, SERVICE), self.users['mgr1'])
        self.assertEqual(self.ops.run_all(self.adm)['skipped']['R01'], 'approved')
        rows = {r['store'].pk: r['label'] for r in self.ops.store_runs()}
        self.assertEqual(rows, {'R01': 'Đã duyệt', 'R02': 'Chưa có kiểm kho'})


    def test_admin_api_permissions(self):
        urls = ['/api/admin/forecast/run/', '/api/admin/forecast/run-all/', '/api/admin/stores/save/',
                '/api/admin/accounts/save/', '/api/admin/accounts/disable/', '/api/admin/accounts/reset-password/',
                '/api/admin/config/save/', '/api/admin/data/import/']
        for u in urls:
            self.assertEqual(self.post(self.client, u).status_code, 401, u)
        self.client.force_login(self.users['mgr1'])
        for u in urls:
            self.assertEqual(self.post(self.client, u).status_code, 403, u)
        self.client.force_login(self.adm)
        for page in ('data', 'model', 'stores', 'accounts', 'config'):
            self.assertEqual(self.client.get(f'/admin-{page}/').status_code, 200, page)

    def test_admin_api_account_and_config(self):
        self.client.force_login(self.adm)
        r = self.post(self.client, '/api/admin/accounts/save/', {'original': '', 'name': 'A', 'username': 'a.new', 'role': 'Nhân viên bếp/kho', 'scope': 'R02 · W'}).json()
        self.assertTrue(r['ok'] and r['temp_password'])
        dup = self.post(self.client, '/api/admin/accounts/save/', {'original': '', 'name': 'A', 'username': 'a.new', 'role': 'Nhân viên bếp/kho', 'scope': 'R02 · W'})
        self.assertEqual((dup.status_code, dup.json()['error']), (409, 'duplicate'))
        self.assertTrue(self.post(self.client, '/api/admin/config/save/', {'service_level': '90%', 'prep_deadline': '11:00', 'inventory_reminder': '20:00'}).json()['ok'])
        self.assertEqual(SystemConfig.get().service_level, 90)


class Round2FixTests(Base):

    def setUp(self):
        super().setUp()
        self.count(self.r01, {'M01': 5, 'M02': 30, 'M03': 100})
        self.mgr = self.users['mgr1']
        for p in (mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast),
                  mock.patch.object(engine, 'save_raw_forecasts', return_value=3)):
            p.start()
            self.addCleanup(p.stop)

    def test_rerun_keeps_adjustment_and_manual_edits(self):
        v1 = plans.create_plan(self.r01, SERVICE, self.mgr)
        plans.set_adjustment(v1, 15, 'Khuyến mãi')
        plans.set_line_qty(v1.lines.get(product_id='M02'), 99)
        v2 = plans.create_plan(self.r01, SERVICE, self.mgr)
        self.assertEqual((v2.version, v2.adjustment_pct, v2.adjustment_reason), (2, 15, 'Khuyến mãi'))
        m01, m02 = v2.lines.get(product_id='M01'), v2.lines.get(product_id='M02')
        self.assertEqual(m01.applied_qty, 130)
        self.assertEqual((m02.need_qty, m02.applied_qty), (38, 99))

    def test_rerun_after_staff_recount_keeps_manual_edit(self):
        v1 = plans.create_plan(self.r01, SERVICE, self.mgr)
        plans.set_line_qty(v1.lines.get(product_id='M01'), 100)
        _, v2 = plans.save_inventory(self.r01, OP_DATE, self.users['stf1'], {'M01': 0, 'M02': 30, 'M03': 100}, draft=False)
        m01 = v2.lines.get(product_id='M01')
        self.assertEqual((m01.need_qty, m01.applied_qty), (120, 100))

    def test_adjustment_keeps_manual_edit(self):
        plan = plans.create_plan(self.r01, SERVICE, self.mgr)
        plans.set_line_qty(plan.lines.get(product_id='M01'), 160)
        plans.set_adjustment(plan, 30, 'Sự kiện tại cửa hàng')
        m01, m02 = plan.lines.get(product_id='M01'), plan.lines.get(product_id='M02')
        self.assertEqual((m01.need_qty, m01.applied_qty), (145, 160))
        self.assertEqual(m02.applied_qty, 45)

    def test_prep_page_shows_adjusted_forecast(self):
        plan = plans.create_plan(self.r01, SERVICE, self.mgr)
        plans.set_adjustment(plan, 30, 'Sự kiện tại cửa hàng')
        self.client.force_login(self.mgr)
        self.assertContains(self.client.get('/prep/?date=31/10/2025&level=all'), 'data-fc="130"')
        csv_text = self.client.get('/prep/export/?date=31/10/2025').content.decode('utf-8-sig')
        self.assertIn('Classic Cheeseburger,chiếc,130,20,5,145,145,Thiếu hàng', csv_text)

    def test_reopen_button_and_locked_run(self):
        plan = plans.create_plan(self.r01, SERVICE, self.mgr)
        plans.approve(plan, self.mgr)
        self.client.force_login(self.mgr)
        page = self.client.get('/prep/?date=31/10/2025').content.decode()
        self.assertIn('data-act="prep-reopen"', page)
        self.assertRegex(page, r'data-act="prep-run" data-date="[^"]*" disabled ')
        self.assertIn('Đã duyệt</span>', page)
        plans.reopen(plan)
        page = self.client.get('/prep/?date=31/10/2025').content.decode()
        self.assertNotIn('data-act="prep-reopen"', page)
        self.assertNotRegex(page, r'data-act="prep-run" data-date="[^"]*" disabled ')
        self.assertIn('Đã mở lại', page)

    def test_auto_publish_has_no_approver(self):
        SystemConfig.objects.filter(pk=1).update(require_approval=False)
        plan = plans.create_plan(self.r01, SERVICE, self.users['stf1'])
        self.assertEqual((plan.status, plan.approved_by), (PrepPlan.Status.APPROVED, None))
        self.client.force_login(self.users['stf1'])
        self.assertContains(self.client.get('/staff/prep/'), 'Tự động gửi bếp')

    def test_dashboard_chart_uses_forecasts_after_operating_date(self):
        plans.create_plan(self.r01, SERVICE, self.mgr)
        self.client.force_login(self.mgr)
        r = self.client.get('/dashboard/?date=05/11/2025')
        bar = next(b for b in r.context['bars'] if b['label'] == SERVICE)
        self.assertEqual((bar['value'], bar['forecast']), (155, True))

    def test_server_error_message_is_generic(self):
        self.client.force_login(self.mgr)
        with mock.patch.object(plans, 'create_plan', side_effect=RuntimeError("(1062, Duplicate entry 'x')")):
            r = self.post(self.client, '/api/forecast/run/', {'date': '31/10/2025'})
        self.assertEqual(r.status_code, 500)
        self.assertNotIn('Duplicate', r.json()['message'])


class Round2SecurityTests(Base):
    def test_login_page_lists_only_demo_accounts(self):
        r = self.client.get('/login/')
        self.assertNotContains(r, 'mgr1')
        self.assertNotContains(r, 'stf1')

    def test_password_reset_same_answer_and_rate_limited(self):
        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)
        known = self.post(self.client, '/api/password-reset/', {'username': 'mgr1'})
        unknown = self.post(self.client, '/api/password-reset/', {'username': 'khong.co'})
        self.assertEqual((known.status_code, unknown.status_code), (200, 200))
        for _ in range(3):
            self.post(self.client, '/api/password-reset/', {'username': 'mgr1'})
        self.assertEqual(self.post(self.client, '/api/password-reset/', {'username': 'mgr1'}).status_code, 429)
        self.assertEqual(Notification.objects.filter(title__startswith='Yêu cầu cấp lại mật khẩu').count(), 1)

    def test_model_page_opens_without_model_file(self):
        self.client.force_login(self.users['adm'])
        with mock.patch.object(engine, 'trained_model', side_effect=RuntimeError('missing')):
            r = self.client.get('/admin-model/')
        self.assertContains(r, 'Không nạp được mô hình')


FAKE_SHAP = (25.0, {pid: {'predicted': 70.0, 'values': {'roll_mean_28': 60.0, 'roll_mean_7': 65.0, 'is_promotion': 1, 'day_of_week_num': 4},
                          'shap': {'roll_mean_28': 30.0, 'roll_mean_7': 10.0, 'is_promotion': 8.0, 'day_of_week_num': -3.0}}
                     for pid in ('M01', 'M02', 'M03')})


@mock.patch.object(explain, 'store_explanation', return_value=FAKE_SHAP)
@mock.patch.object(engine, 'save_raw_forecasts', return_value=3)
@mock.patch.object(engine, 'forecast_store', side_effect=fake_forecast)
class ExplainTests(Base):

    def setUp(self):
        super().setUp()
        self.count(self.r01, {'M01': 5, 'M02': 5, 'M03': 5})

    def line(self):
        plan = plans.create_plan(self.r01, SERVICE, self.users['mgr1'])
        return plan.lines.get(product_id='M01')

    def test_manager_sees_business_groups(self, *_):
        line = self.line()
        self.client.force_login(self.users['mgr1'])
        data = self.client.get(f'/api/line/{line.pk}/reason/').json()
        labels = {i['label']: i['value'] for i in data['contrib']['items']}
        self.assertEqual(labels['Lượng bán gần đây'], 40.0)
        self.assertEqual(labels['Khuyến mãi'], 8.0)
        self.assertEqual(labels['Thứ trong tuần'], -3.0)
        self.assertNotIn('roll_mean_28', json.dumps(data['contrib']))

    def test_manager_cannot_use_admin_explain_or_other_store(self, *_):
        line = self.line()
        self.client.force_login(self.users['mgr1'])
        self.assertEqual(self.client.get('/api/admin/explain/?store=R01').status_code, 403)
        self.client.force_login(self.users['mgr2'])
        self.assertEqual(self.client.get(f'/api/line/{line.pk}/reason/').status_code, 404)

    def test_staff_cannot_see_shap(self, *_):
        line = self.line()
        self.client.force_login(self.users['stf1'])
        self.assertEqual(self.client.get(f'/api/line/{line.pk}/reason/').status_code, 403)
        self.assertEqual(self.client.get('/api/admin/explain/?store=R01').status_code, 403)

    def test_admin_sees_any_store_and_technical_detail(self, *_):
        line = self.line()
        self.client.force_login(self.users['adm'])
        self.assertEqual(self.client.get(f'/api/line/{line.pk}/reason/').status_code, 200)
        data = self.client.get('/api/admin/explain/?store=R02&product=M01').json()
        self.assertTrue(data['ok'], data)
        self.assertEqual(data['importance_features'][0]['column'], 'roll_mean_28')
        self.assertEqual(data['importance_groups'][0]['label'], 'Lượng bán gần đây')
        self.assertAlmostEqual(sum(g['share'] for g in data['importance_groups']), 100, delta=2)
        self.assertTrue(data['item']['unit'])
        self.assertEqual(data['item']['features'][0]['column'], 'roll_mean_28')
        self.assertEqual(data['item']['features'][0]['value'], '60')

    def test_admin_explain_validation(self, *_):
        self.client.force_login(self.users['adm'])
        self.assertEqual(self.client.get('/api/admin/explain/?store=ZZZ').status_code, 404)
        self.assertEqual(self.client.get('/api/admin/explain/?store=R01&date=2024-03-15').json()['error'], 'out_of_range')
        self.assertEqual(self.client.get('/api/admin/explain/?store=R01&product=XXX').status_code, 404)

    def test_admin_model_page_has_shap_section_manager_does_not(self, *_):
        self.client.force_login(self.users['adm'])
        self.assertContains(self.client.get('/admin-model/'), 'id="shap-box"')
        self.client.force_login(self.users['mgr1'])
        self.assertEqual(self.client.get('/admin-model/').status_code, 403)
