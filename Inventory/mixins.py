from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import redirect


class ProtectedDeleteMixin:
    """Show a friendly message instead of crashing when a protected row is deleted."""
    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request,
                           "This record cannot be deleted because it has borrowing history.")
            return redirect(self.get_success_url())