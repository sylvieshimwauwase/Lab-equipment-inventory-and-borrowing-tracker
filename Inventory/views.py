from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import CategoryForm, ItemForm
from .mixins import ProtectedDeleteMixin
from .models import Category, Item
from .pagination import paginate


# ---------------- Items ----------------
@login_required
def item_list(request):
    items = Item.objects.select_related('category')

    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    available = request.GET.get('available', '')

    if q:
        items = items.filter(Q(name__icontains=q) | Q(serial_number__icontains=q))
    if category_id:
        items = items.filter(category_id=category_id)
    if available in ('yes', 'no'):
        items = items.filter(is_available=(available == 'yes'))

    page_obj, querystring = paginate(request, items)
    context = {
        'items': page_obj,
        'page_obj': page_obj,
        'querystring': querystring,
        'categories': Category.objects.all(),
        'q': q,
        'selected_category': category_id,
        'selected_available': available,
    }
    return render(request, 'inventory/item_list.html', context)


class ItemDetailView(LoginRequiredMixin, DetailView):
    model = Item
    template_name = 'inventory/item_detail.html'
    context_object_name = 'item'


class ItemCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'Inventory.add_item'
    model = Item
    form_class = ItemForm
    template_name = 'form.html'
    success_url = reverse_lazy('inventory:item_list')
    success_message = "Item was added successfully."
    extra_context = {'title': 'Add Item', 'back_url': reverse_lazy('inventory:item_list')}


class ItemUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'Inventory.change_item'
    model = Item
    form_class = ItemForm
    template_name = 'form.html'
    success_url = reverse_lazy('inventory:item_list')
    success_message = "Item was updated successfully."
    extra_context = {'title': 'Edit Item', 'back_url': reverse_lazy('inventory:item_list')}


class ItemDeleteView(PermissionRequiredMixin, ProtectedDeleteMixin, SuccessMessageMixin, DeleteView):
    permission_required = 'Inventory.delete_item'
    model = Item
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('inventory:item_list')
    success_message = "Item was deleted."
    extra_context = {
        'title': 'Delete Item',
        'warning': 'Items that have borrowing history cannot be deleted.',
        'back_url': reverse_lazy('inventory:item_list'),
    }


# ---------------- Categories ----------------
class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

    def get_queryset(self):
        return Category.objects.annotate(item_count=Count('items')).order_by('name')


class CategoryCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'Inventory.add_category'
    model = Category
    form_class = CategoryForm
    template_name = 'form.html'
    success_url = reverse_lazy('inventory:category_list')
    success_message = "Category was added successfully."
    extra_context = {'title': 'Add Category', 'back_url': reverse_lazy('inventory:category_list')}


class CategoryUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'Inventory.change_category'
    model = Category
    form_class = CategoryForm
    template_name = 'form.html'
    success_url = reverse_lazy('inventory:category_list')
    success_message = "Category was updated successfully."
    extra_context = {'title': 'Edit Category', 'back_url': reverse_lazy('inventory:category_list')}


class CategoryDeleteView(PermissionRequiredMixin, ProtectedDeleteMixin, SuccessMessageMixin, DeleteView):
    permission_required = 'Inventory.delete_category'
    model = Category
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('inventory:category_list')
    success_message = "Category was deleted."
    extra_context = {
        'title': 'Delete Category',
        'warning': 'A category that still contains items cannot be deleted.',
        'back_url': reverse_lazy('inventory:category_list'),
    }