from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('risk-check/', views.risk_check, name='risk_check'),
]