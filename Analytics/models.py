from django.db import models

from Borrowing.models import BorrowRecord


class RiskPrediction(models.Model):
    """The model's estimate that a borrowing will be returned late."""
    LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    # Derived data: if the borrow record is deleted, its prediction goes with it
    record = models.OneToOneField(
        BorrowRecord, on_delete=models.CASCADE, related_name='risk')
    probability = models.FloatField()
    level = models.CharField(max_length=6, choices=LEVEL_CHOICES)
    model_trained_at = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.record} - {self.get_level_display()} ({self.percent}%)"

    @property
    def percent(self):
        return round(self.probability * 100)