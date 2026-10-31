"""
URL configuration for Brightloop Software - Subscription Management System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls', namespace='dashboard')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('products/', include('products.urls', namespace='products')),
    path('plans/', include('plans.urls', namespace='plans')),
    path('subscriptions/', include('subscriptions.urls', namespace='subscriptions')),
    path('billing/', include('billing.urls', namespace='billing')),
    path('payments/', include('payments.urls', namespace='payments')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
