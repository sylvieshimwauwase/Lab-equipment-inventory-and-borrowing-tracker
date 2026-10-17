from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from Inventory.models import Item


class Borrower(models.Model):
    full_name = models.CharField(max_length=150)
    student_id = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=100)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"


class BorrowRecordQuerySet(models.QuerySet):
    def active(self):
        """Records not yet returned."""
        return self.filter(status='borrowed')

    def overdue(self):
        """Not returned and past the due date."""
        return self.active().filter(due_date__lt=date.today())


class BorrowRecord(models.Model):
    STATUS_CHOICES = [
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
    ]

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='borrow_records')
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT, related_name='borrow_records')
    date_borrowed = models.DateField()
    due_date = models.DateField()
    date_returned = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                              default='borrowed', editable=False)

    objects = BorrowRecordQuerySet.as_manager()

    class Meta:
        ordering = ['-date_borrowed']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F('date_borrowed')),
                name='due_date_not_before_borrowed'),
            models.CheckConstraint(
                condition=models.Q(date_returned__isnull=True)
                | models.Q(date_returned__gte=models.F('date_borrowed')),
                name='returned_not_before_borrowed'),
        ]

    def __str__(self):
        return f"{self.item.name} to {self.borrower.full_name}"

    # ----- computed values -----
    @property
    def is_overdue(self):
        return self.date_returned is None and self.due_date < date.today()

    @property
    def display_status(self):
        if self.status == 'returned':
            return 'Returned'
        return 'Overdue' if self.is_overdue else 'Borrowed'

    # ----- validation (runs in forms AND in the admin) -----
    def clean(self):
        errors = {}
        if self.date_borrowed and self.due_date and self.due_date < self.date_borrowed:
            errors['due_date'] = "Due date cannot be earlier than the borrow date."
        if self.date_borrowed and self.date_returned and self.date_returned < self.date_borrowed:
            errors['__all__'] = "Return date cannot be earlier than the borrow date."
        if self.item_id and not self.date_returned:
            if self.item.condition == 'damaged':
                errors['item'] = "A damaged item cannot be borrowed."
            elif BorrowRecord.objects.filter(
                    item_id=self.item_id, status='borrowed').exclude(pk=self.pk).exists():
                errors['item'] = "This item is already borrowed."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # status always follows date_returned, so the two can never disagree
        self.status = 'returned' if self.date_returned else 'borrowed'
        super().save(*args, **kwargs)