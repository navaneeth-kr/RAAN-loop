from django.contrib import admin
from .models import Customer, Subscription, Invoice

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'company_name', 'email', 'phone', 'country', 'status')
    search_fields = ('full_name', 'company_name', 'email')
    list_filter = ('status', 'country')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('subscription_id', 'customer', 'plan', 'status', 'current_amount', 'start_date', 'next_billing_date')
    list_filter = ('status', 'billing_cycle')
    search_fields = ('subscription_id', 'customer__full_name', 'customer__email', 'plan__name')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'total_amount', 'status', 'issued_date')
    list_filter = ('status', 'issued_date')
    search_fields = ('invoice_number', 'customer__full_name')
