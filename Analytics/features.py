from django.db.models import F

from Borrowing.models import BorrowRecord

# Inputs of the model, in this exact order
FEATURES = [
    'borrow_days',          # days between the borrow date and the due date
    'weekday',              # 0 = Monday ... 6 = Sunday
    'prior_borrowings',     # how many borrowings the borrower already returned
    'prior_late_rate',      # share of those returned late (0 to 1)
    'item_times_borrowed',  # how often this item was borrowed before
    'item_fair',            # 1 if the item's condition is "fair"
]


def record_features(item, borrower, date_borrowed, due_date):
    """Build the model inputs for one borrowing, using only the history before it."""
    past = BorrowRecord.objects.filter(
        borrower=borrower,
        date_returned__isnull=False,
        date_borrowed__lt=date_borrowed,
    )
    prior_borrowings = past.count()
    prior_late = past.filter(date_returned__gt=F('due_date')).count()

    return {
        'borrow_days': (due_date - date_borrowed).days,
        'weekday': date_borrowed.weekday(),
        'prior_borrowings': prior_borrowings,
        'prior_late_rate': round(prior_late / prior_borrowings, 3) if prior_borrowings else 0.0,
        'item_times_borrowed': BorrowRecord.objects.filter(
            item=item, date_borrowed__lt=date_borrowed).count(),
        'item_fair': 1 if item.condition == 'fair' else 0,
    }