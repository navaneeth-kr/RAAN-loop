from django.contrib import admin
from .models import ProductCategory, Product, ProductVariant

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'status', 'base_price', 'is_featured', 'created_at')
    list_filter = ('status', 'category', 'is_featured')
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'product', 'tier', 'billing_cycle', 'price', 'is_active')
    list_filter = ('tier', 'billing_cycle', 'is_active')
    search_fields = ('name', 'sku', 'product__name')
