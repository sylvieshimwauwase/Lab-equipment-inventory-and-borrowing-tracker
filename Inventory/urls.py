from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Items
    path('items/', views.item_list, name='item_list'),
    path('items/add/', views.ItemCreateView.as_view(), name='item_add'),
    path('items/<int:pk>/', views.ItemDetailView.as_view(), name='item_detail'),
    path('items/<int:pk>/edit/', views.ItemUpdateView.as_view(), name='item_edit'),
    path('items/<int:pk>/delete/', views.ItemDeleteView.as_view(), name='item_delete'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
]