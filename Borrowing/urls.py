from django.urls import path
from . import views

app_name = 'borrowing'

urlpatterns = [
    path('', views.record_list, name='record_list'),
    path('new/', views.BorrowCreateView.as_view(), name='borrow_new'),
    path('<int:pk>/return/', views.return_item, name='return_item'),

    path('borrowers/', views.BorrowerListView.as_view(), name='borrower_list'),
    path('borrowers/add/', views.BorrowerCreateView.as_view(), name='borrower_add'),
    path('borrowers/<int:pk>/edit/', views.BorrowerUpdateView.as_view(), name='borrower_edit'),
    path('borrowers/<int:pk>/delete/', views.BorrowerDeleteView.as_view(), name='borrower_delete'),
]