"""
URL configuration for Dalooneh project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from .views import home_view, test_phone_modal, management_login_view, management_logout_view, management_dashboard, custom_logout_view, manifest_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('menu/', include('menu.urls')),
    path('orders/', include('orders.urls')),
    path('customers/', include('customers.urls')),
    path('staff/', include('staff.urls')),
    path('tables/', include('tables.urls')),
    path('notifications/', include('notifications.urls')),
    path('', home_view, name='home'),
    path('test-phone-modal/', test_phone_modal, name='test_phone_modal'),
    path('websocket-test/', TemplateView.as_view(template_name='websocket_test.html'), name='websocket_test'),
    path('logout/', custom_logout_view, name='logout'),
    
    # PWA URLs
    path('manifest.json', manifest_view, name='manifest'),
    
    # Management panel URLs
    path('management/login/', management_login_view, name='management_login'),
    path('management/logout/', management_logout_view, name='management_logout'),
    path('management/', management_dashboard, name='management_dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
