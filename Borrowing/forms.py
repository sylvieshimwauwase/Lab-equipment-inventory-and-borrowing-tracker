import re
from datetime import date
from django import forms
from Inventory.forms import BootstrapFormMixin
from Inventory.models import Item
from .models import Borrower, BorrowRecord


class BorrowerForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Borrower
        fields = ['full_name', 'student_id', 'phone', 'email', 'department']

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not re.fullmatch(r'\+?\d{9,15}', phone):
            raise forms.ValidationError("Enter a valid phone number (9 to 15 digits, optional +).")
        return phone


class BorrowRecordForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = BorrowRecord
        fields = ['item', 'borrower', 'date_borrowed', 'due_date']
        widgets = {
            'date_borrowed': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show items that are free to borrow
        self.fields['item'].queryset = Item.objects.filter(is_available=True)
        self.fields['date_borrowed'].initial = date.today()

    def clean(self):
        cleaned = super().clean()
        borrowed = cleaned.get('date_borrowed')
        due = cleaned.get('due_date')
        if borrowed and due and due < borrowed:
            raise forms.ValidationError("Due date cannot be earlier than the borrow date.")
        return cleaned