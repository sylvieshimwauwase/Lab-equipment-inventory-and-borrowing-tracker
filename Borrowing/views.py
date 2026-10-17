from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from Inventory.mixins import ProtectedDeleteMixin
from Inventory.pagination import paginate
from .forms import BorrowerForm, BorrowRecordForm
from .models import Borrower, BorrowRecord


# ---------- Borrow records ----------
@login_required
def record_list(request):
    records = BorrowRecord.objects.select_related('item', 'borrower').order_by('-date_borrowed', '-pk')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if q:
        records = records.filter(
            Q(item__name__icontains=q) | Q(item__serial_number__icontains=q) |
            Q(borrower__full_name__icontains=q) | Q(borrower__student_id__icontains=q))
    if status == 'overdue':
        records = records.overdue()
    elif status == 'borrowed':
        records = records.active().filter(due_date__gte=date.today())
    elif status == 'returned':
        records = records.filter(status='returned')

    page_obj, querystring = paginate(request, records)
    context = {
        'records': page_obj,
        'page_obj': page_obj,
        'querystring': querystring,
        'q': q,
        'selected_status': status,
    }
    return render(request, 'borrowing/record_list.html', context)


class BorrowCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'Borrowing.add_borrowrecord'
    model = BorrowRecord
    form_class = BorrowRecordForm
    template_name = 'form.html'
    success_url = reverse_lazy('borrowing:record_list')
    extra_context = {'title': 'Borrow an Item', 'back_url': reverse_lazy('borrowing:record_list')}

    def form_valid(self, form):
        with transaction.atomic():
            record = form.save()      # the signal marks the item unavailable
        messages.success(self.request, f"{record.item.name} was lent to {record.borrower.full_name}.")
        return redirect(self.success_url)


@login_required
@permission_required('Borrowing.change_borrowrecord', raise_exception=True)
@require_POST
def return_item(request, pk):
    with transaction.atomic():
        record = get_object_or_404(BorrowRecord.objects.select_for_update(), pk=pk)
        if record.status == 'returned':
            messages.info(request, "This item was already returned.")
        else:
            record.date_returned = date.today()
            record.save()             # the signal makes the item available again
            messages.success(request, f"{record.item.name} was returned.")
    return redirect('borrowing:record_list')


# ---------- Borrowers ----------
class BorrowerListView(LoginRequiredMixin, ListView):
    model = Borrower
    template_name = 'borrowing/borrower_list.html'
    context_object_name = 'borrowers'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        department = self.request.GET.get('department', '')
        if q:
            qs = qs.filter(Q(full_name__icontains=q) | Q(student_id__icontains=q) |
                           Q(phone__icontains=q))
        if department:
            qs = qs.filter(department=department)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        context.update({
            'q': self.request.GET.get('q', '').strip(),
            'selected_department': self.request.GET.get('department', ''),
            'departments': Borrower.objects.order_by('department')
                                   .values_list('department', flat=True).distinct(),
            'querystring': params.urlencode(),
        })
        return context


class BorrowerCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'Borrowing.add_borrower'
    model = Borrower
    form_class = BorrowerForm
    template_name = 'form.html'
    success_url = reverse_lazy('borrowing:borrower_list')
    success_message = "Borrower was added successfully."
    extra_context = {'title': 'Add Borrower', 'back_url': reverse_lazy('borrowing:borrower_list')}


class BorrowerUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'Borrowing.change_borrower'
    model = Borrower
    form_class = BorrowerForm
    template_name = 'form.html'
    success_url = reverse_lazy('borrowing:borrower_list')
    success_message = "Borrower was updated successfully."
    extra_context = {'title': 'Edit Borrower', 'back_url': reverse_lazy('borrowing:borrower_list')}


class BorrowerDeleteView(PermissionRequiredMixin, ProtectedDeleteMixin, SuccessMessageMixin, DeleteView):
    permission_required = 'Borrowing.delete_borrower'
    model = Borrower
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('borrowing:borrower_list')
    success_message = "Borrower was deleted."
    extra_context = {
        'title': 'Delete Borrower',
        'warning': 'Borrowers that have borrowing history cannot be deleted.',
        'back_url': reverse_lazy('borrowing:borrower_list'),
    }