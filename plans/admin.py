from django.contrib import admin
from .models import SubscriptionPlan, PlanFeature

class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 2

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'product', 'tier', 'billing_cycle', 'price', 'trial_days', 'status', 'is_featured')
    list_filter = ('tier', 'billing_cycle', 'status', 'is_featured')
    search_fields = ('name', 'code', 'product__name')
    inlines = [PlanFeatureInline]

@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan', 'quota_value', 'is_included', 'sort_order')
    list_filter = ('is_included', 'plan')
