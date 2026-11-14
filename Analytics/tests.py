import json
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from sklearn.ensemble import RandomForestClassifier

from Analytics.features import FEATURES, record_features
from Analytics.management.commands.train_model import make_synthetic
from Analytics.models import RiskPrediction
from Analytics.predictor import predict_borrowing, risk_level
from Borrowing.models import Borrower, BorrowRecord
from Inventory.models import Category, Item

# A small model trained once, used in place of the saved model file
_data = make_synthetic(300, seed=1)
_model = RandomForestClassifier(n_estimators=20, random_state=1).fit(
    _data[FEATURES], _data['returned_late'])
FAKE_BUNDLE = {'model': _model, 'features': FEATURES}


class AnalyticsTestCase(TestCase):
    """Shared sample data, with the prediction model replaced by FAKE_BUNDLE."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Computers')
        cls.item = Item.objects.create(
            name='Dell Laptop', serial_number='DL-001', category=cls.category)
        cls.borrower = Borrower.objects.create(
            full_name='Jane Uwase', student_id='2024001',
            phone='0788123456', department='Computer Science')
        cls.user = User.objects.create_user('staff1', password='pass12345')
        cls.admin = User.objects.create_superuser('admin', 'a@example.com', 'pass12345')

    def setUp(self):
        patcher = patch('Analytics.predictor._load', return_value=FAKE_BUNDLE)
        patcher.start()
        self.addCleanup(patcher.stop)

    def lend(self, item=None, days=7, returned=None):
        today = date.today()
        return BorrowRecord.objects.create(
            item=item or self.item, borrower=self.borrower,
            date_borrowed=today, due_date=today + timedelta(days=days),
            date_returned=returned)


class FeatureTests(AnalyticsTestCase):

    def test_borrow_days_is_the_gap_between_dates(self):
        today = date.today()
        features = record_features(self.item, self.borrower, today, today + timedelta(days=9))
        self.assertEqual(features['borrow_days'], 9)

    def test_history_features_use_past_returned_borrowings(self):
        today = date.today()
        old_item = Item.objects.create(
            name='Old Cable', serial_number='OC-001', category=self.category)
        BorrowRecord.objects.create(
            item=old_item, borrower=self.borrower,
            date_borrowed=today - timedelta(days=30),
            due_date=today - timedelta(days=20),
            date_returned=today - timedelta(days=10))      # returned late
        features = record_features(self.item, self.borrower, today, today + timedelta(days=5))
        self.assertEqual(features['prior_borrowings'], 1)
        self.assertEqual(features['prior_late_rate'], 1.0)

    def test_item_condition_flag(self):
        fair = Item.objects.create(
            name='Projector', serial_number='PJ-001',
            category=self.category, condition='fair')
        today = date.today()
        features = record_features(fair, self.borrower, today, today + timedelta(days=5))
        self.assertEqual(features['item_fair'], 1)


class PredictorTests(AnalyticsTestCase):

    def test_prediction_has_probability_and_level(self):
        today = date.today()
        result = predict_borrowing(self.item, self.borrower, today, today + timedelta(days=7))
        self.assertTrue(0 <= result['probability'] <= 1)
        self.assertIn(result['level'], ('low', 'medium', 'high'))

    def test_missing_model_returns_none(self):
        today = date.today()
        with patch('Analytics.predictor._load', return_value=None):
            result = predict_borrowing(self.item, self.borrower, today, today + timedelta(days=7))
        self.assertIsNone(result)

    def test_risk_level_thresholds(self):
        self.assertEqual(risk_level(0.10), 'low')
        self.assertEqual(risk_level(0.50), 'medium')
        self.assertEqual(risk_level(0.90), 'high')


class SignalTests(AnalyticsTestCase):

    def test_new_borrowing_is_scored_automatically(self):
        record = self.lend()
        self.assertTrue(RiskPrediction.objects.filter(record=record).exists())

    def test_returned_borrowing_is_not_scored(self):
        record = self.lend(returned=date.today())
        self.assertFalse(RiskPrediction.objects.filter(record=record).exists())

    def test_borrowing_works_when_model_is_missing(self):
        with patch('Analytics.predictor._load', return_value=None):
            record = self.lend()
        self.assertTrue(BorrowRecord.objects.filter(pk=record.pk).exists())
        self.assertFalse(RiskPrediction.objects.filter(record=record).exists())

    def test_prediction_error_never_blocks_borrowing(self):
        with patch('Analytics.signals.predict_borrowing', side_effect=RuntimeError('boom')):
            with self.assertLogs('Analytics.signals', level='ERROR'):
                record = self.lend()
        self.assertTrue(BorrowRecord.objects.filter(pk=record.pk).exists())

    def test_deleting_a_record_removes_its_prediction(self):
        record = self.lend()
        record.delete()
        self.assertEqual(RiskPrediction.objects.count(), 0)


class AnalyticsApiTests(AnalyticsTestCase):

    def payload(self, **extra):
        data = {'item': self.item.pk, 'borrower': self.borrower.pk,
                'due_date': (date.today() + timedelta(days=7)).isoformat()}
        data.update(extra)
        return data

    def test_predict_requires_login(self):
        response = self.client.post(
            '/api/predict/', self.payload(), content_type='application/json')
        self.assertIn(response.status_code, (401, 403))

    def test_predict_returns_a_prediction(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/predict/', self.payload(), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body['level'], ('low', 'medium', 'high'))
        self.assertTrue(0 <= body['percent'] <= 100)

    def test_predict_rejects_due_date_before_borrow_date(self):
        self.client.force_login(self.user)
        data = self.payload(due_date=(date.today() - timedelta(days=2)).isoformat())
        response = self.client.post('/api/predict/', data, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_predict_reports_missing_model(self):
        self.client.force_login(self.user)
        with patch('Analytics.predictor._load', return_value=None):
            response = self.client.post(
                '/api/predict/', self.payload(), content_type='application/json')
        self.assertEqual(response.status_code, 503)

    def test_training_data_is_admin_only(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/training-data/').status_code, 403)

    def test_training_data_lists_returned_borrowings(self):
        self.lend(returned=date.today())
        self.client.force_login(self.admin)
        response = self.client.get('/api/training-data/')
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual(len(rows), 1)
        self.assertIn('returned_late', rows[0])


class PagesTests(AnalyticsTestCase):

    def test_risk_check_requires_login(self):
        response = self.client.get(reverse('analytics:risk_check'))
        self.assertEqual(response.status_code, 302)

    def test_risk_check_shows_a_prediction(self):
        self.client.force_login(self.user)
        today = date.today()
        response = self.client.post(reverse('analytics:risk_check'), {
            'item': self.item.pk,
            'borrower': self.borrower.pk,
            'date_borrowed': today.isoformat(),
            'due_date': (today + timedelta(days=7)).isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['result'])

    def test_dashboard_lists_scored_borrowings(self):
        self.lend()
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dell Laptop')


class SyntheticDataTests(TestCase):

    def test_synthetic_data_has_both_outcomes_and_all_features(self):
        data = make_synthetic(500, seed=3)
        self.assertEqual(set(data['returned_late']), {0, 1})
        for name in FEATURES:
            self.assertIn(name, data.columns)