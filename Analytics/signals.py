import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from Borrowing.models import BorrowRecord
from .models import RiskPrediction
from .predictor import model_info, predict_borrowing

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BorrowRecord)
def score_new_borrowing(sender, instance, created, raw=False, **kwargs):
    """Score every new borrowing that has not been returned yet."""
    if raw or not created or instance.date_returned:
        return
    try:
        result = predict_borrowing(
            instance.item, instance.borrower, instance.date_borrowed, instance.due_date)
        if result is None:
            return  # no model file yet: the app keeps working without a score
        info = model_info() or {}
        with transaction.atomic():
            RiskPrediction.objects.update_or_create(
                record=instance,
                defaults={
                    'probability': result['probability'],
                    'level': result['level'],
                    'model_trained_at': info.get('trained_at', ''),
                })
    except Exception:
        # A prediction problem must never stop someone from borrowing an item
        logger.exception('Risk prediction failed for borrowing %s', instance.pk)
