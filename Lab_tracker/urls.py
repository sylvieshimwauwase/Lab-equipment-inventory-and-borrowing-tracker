from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import include, path

from Analytics import api as analytics_api
from Inventory import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Dashboard (home)
    path('', dashboard.dashboard, name='dashboard'),

    # Health check for hosting
    path('health/', lambda request: HttpResponse('ok'), name='health'),

    # App URLs
    path('inventory/', include('Inventory.urls')),
    path('borrowing/', include('Borrowing.urls')),
    path('analytics/', include('Analytics.urls')),

    # REST API
    path('api/predict/', analytics_api.predict, name='api-predict'),
    path('api/', include('Lab_tracker.api')),
]