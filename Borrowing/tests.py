from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from Inventory.models import Category, Item
from .models import Borrower, BorrowRecord


class BaseTestCase(TestCase):
    """Shared sample data. Django builds a temporary test database for it."""

    @classmethod
    def setUpTestData(cls):
        call_command('setup_roles')
        cls.category = Category.objects.create(name='Computers')
        cls.item = Item.objects.create(
            name='Dell Laptop', serial_number='DL-001', category=cls.category)
        cls.borrower = Borrower.objects.create(
            full_name='Jane Uwase', student_id='2024001',
            phone='0788123456', department='Computer Science')

        cls.admin = User.objects.create_superuser('admin', 'a@example.com', 'pass12345')
        cls.staff = User.objects.create_user('staff1', password='pass12345')
        cls.staff.groups.add(Group.objects.get(name='Staff'))
        cls.manager = User.objects.create_user('manager1', password='pass12345')
        cls.manager.groups.add(Group.objects.get(name='Manager'))

    def lend(self, item=None, borrowed=None, due=None):
        today = date.today()
        return BorrowRecord.objects.create(
            item=item or self.item,
            borrower=self.borrower,
            date_borrowed=borrowed or today,
            due_date=due or today + timedelta(days=7))


class BorrowingLogicTests(BaseTestCase):

    def test_borrowing_makes_item_unavailable(self):
        self.lend()
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_available)

    def test_returning_via_view_frees_item(self):
        record = self.lend()
        self.client.force_login(self.admin)
        self.client.post(reverse('borrowing:return_item', args=[record.pk]))
        record.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(record.status, 'returned')
        self.assertTrue(self.item.is_available)

    def test_deleting_record_frees_item(self):
        record = self.lend()
        record.delete()
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_available)

    def test_due_date_before_borrow_date_is_rejected(self):
        today = date.today()
        record = BorrowRecord(item=self.item, borrower=self.borrower,
                              date_borrowed=today, due_date=today - timedelta(days=1))
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_already_borrowed_item_is_rejected(self):
        self.lend()
        today = date.today()
        second = BorrowRecord(item=self.item, borrower=self.borrower,
                              date_borrowed=today, due_date=today + timedelta(days=3))
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_damaged_item_cannot_be_borrowed(self):
        damaged = Item.objects.create(
            name='Old Projector', serial_number='OP-001',
            category=self.category, condition='damaged')
        self.assertFalse(damaged.is_available)
        today = date.today()
        record = BorrowRecord(item=damaged, borrower=self.borrower,
                              date_borrowed=today, due_date=today + timedelta(days=3))
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_overdue_is_computed_from_due_date(self):
        today = date.today()
        record = self.lend(borrowed=today - timedelta(days=10), due=today - timedelta(days=3))
        self.assertTrue(record.is_overdue)
        self.assertEqual(record.display_status, 'Overdue')
        self.assertEqual(BorrowRecord.objects.overdue().count(), 1)

    def test_returned_record_is_not_overdue(self):
        today = date.today()
        record = self.lend(borrowed=today - timedelta(days=10), due=today - timedelta(days=3))
        record.date_returned = today
        record.save()
        self.assertFalse(record.is_overdue)
        self.assertEqual(record.status, 'returned')


class AccessControlTests(BaseTestCase):

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_dashboard_loads_for_logged_in_user(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_staff_cannot_delete_item(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('inventory:item_delete', args=[self.item.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())

    def test_manager_can_delete_unused_item(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('inventory:item_delete', args=[self.item.pk]))
        self.assertFalse(Item.objects.filter(pk=self.item.pk).exists())

    def test_item_with_history_is_protected(self):
        self.lend()
        self.client.force_login(self.manager)
        self.client.post(reverse('inventory:item_delete', args=[self.item.pk]))
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())

    def test_staff_can_add_item(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('inventory:item_add'), {
            'name': 'HDMI Cable', 'serial_number': 'hc-001',
            'category': self.category.pk, 'condition': 'good'})
        self.assertTrue(Item.objects.filter(serial_number='HC-001').exists())


class APITests(BaseTestCase):

    def test_api_requires_login(self):
        response = self.client.get('/api/items/')
        self.assertIn(response.status_code, (401, 403))

    def test_api_lists_items(self):
        self.client.force_login(self.staff)
        response = self.client.get('/api/items/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_api_overdue_filter(self):
        today = date.today()
        self.lend(borrowed=today - timedelta(days=10), due=today - timedelta(days=3))
        self.client.force_login(self.staff)
        response = self.client.get('/api/borrow-records/?status=overdue')
        self.assertEqual(response.json()['count'], 1)