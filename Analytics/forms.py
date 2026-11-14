from datetime import date, timedelta

from django import forms

from Borrowing.models import Borrower
from Inventory.forms import BootstrapFormMixin
from Inventory.models import Item


class RiskCheckForm(BootstrapFormMixin, forms.Form):
    item = forms.ModelChoiceField(queryset=Item.objects.none())
    borrower = forms.ModelChoiceField(queryset=Borrower.objects.all())
    date_borrowed = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}), initial=date.today)
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=lambda: date.today() + timedelta(days=7))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = Item.objects.filter(is_available=True)

    def clean(self):
        cleaned = super().clean()
        borrowed, due = cleaned.get('date_borrowed'), cleaned.get('due_date')
        if borrowed and due and due < borrowed:
            raise forms.ValidationError("Due date cannot be earlier than the borrow date.")
        return cleaned