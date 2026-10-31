"""
URL configuration for Brightloop Software - Subscription Management System.
Unified routing supporting all Core, Catalog, Finance, and Foundation modules.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('subscriptions.urls')),
    path('products/', include('products.urls')),
    path('plans/', include('plans.urls')),
    path('accounts/', include('accounts.urls')),
    path('billing/', include('billing.urls')),
    path('gateway-payments/', include('payments.urls')),
    path('overview/', include('dashboard.urls')),

    # Dual namespace compatibility for foundation test suite & modules
    path('catalog/products/', include(('products.urls', 'products'), namespace='products')),
    path('catalog/plans/', include(('plans.urls', 'plans'), namespace='plans')),
    path('sub/subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),
]

if settings.DEBUG:
    if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
