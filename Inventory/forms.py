from django import forms
from .models import Category, Item


class BootstrapFormMixin:
    """Adds Bootstrap classes to every field."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def clean_name(self):
        return self.cleaned_data['name'].strip().title()


class ItemForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'serial_number', 'category', 'condition']

    def clean_serial_number(self):
        return self.cleaned_data['serial_number'].strip().upper()