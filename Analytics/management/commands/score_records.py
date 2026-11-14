from django.core.management.base import BaseCommand, CommandError

from Analytics.models import RiskPrediction
from Analytics.predictor import _load, model_info, predict_borrowing
from Borrowing.models import BorrowRecord


class Command(BaseCommand):
    help = "Score active borrowings with the late-return risk model."

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
                            help='Rescore borrowings that already have a score (after retraining).')

    def handle(self, *args, **options):
        if _load() is None:
            raise CommandError('No model found. Run: python manage.py train_model first.')

        records = BorrowRecord.objects.active().select_related('item', 'borrower')
        if not options['all']:
            records = records.filter(risk__isnull=True)

        trained_at = (model_info() or {}).get('trained_at', '')
        count = 0
        for record in records:
            result = predict_borrowing(
                record.item, record.borrower, record.date_borrowed, record.due_date)
            RiskPrediction.objects.update_or_create(
                record=record,
                defaults={'probability': result['probability'],
                          'level': result['level'],
                          'model_trained_at': trained_at})
            count += 1
        self.stdout.write(self.style.SUCCESS(f'{count} borrowing(s) scored.'))