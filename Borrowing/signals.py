from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BorrowRecord


@receiver([post_save, post_delete], sender=BorrowRecord)
def refresh_item_availability(sender, instance, **kwargs):
    # Item.save() recomputes is_available from its borrow records
    instance.item.save()