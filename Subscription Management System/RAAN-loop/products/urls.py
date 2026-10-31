from django.urls import path
from . import views

urlpatterns = [
    # Products
    path('', views.ProductListView.as_view(), name='product_list'),
    path('catalog/', views.index, name='index'),
    path('new/', views.ProductCreateView.as_view(), name='product_create'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
    path('<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    
    # Variants
    path('variants/', views.VariantListView.as_view(), name='variant_list'),
    path('variants/new/', views.VariantCreateView.as_view(), name='variant_create'),
    path('variants/<int:pk>/edit/', views.VariantUpdateView.as_view(), name='variant_update'),
    path('variants/<int:pk>/delete/', views.VariantDeleteView.as_view(), name='variant_delete'),
]
