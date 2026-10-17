from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):
    """One physical unit of equipment (so 3 laptops = 3 rows)."""
    CONDITION_CHOICES = [
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('damaged', 'Damaged'),
    ]

    name = models.CharField(max_length=150)
    serial_number = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,          # a category with items cannot be deleted
        related_name='items'
    )
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='good')
    is_available = models.BooleanField(default=True, editable=False)  # computed, not typed
    date_added = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    def save(self, *args, **kwargs):
        # Available = not damaged AND not currently on loan
        on_loan = self.pk is not None and self.borrow_records.filter(status='borrowed').exists()
        self.is_available = self.condition != 'damaged' and not on_loan
        super().save(*args, **kwargs)