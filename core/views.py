import csv
import json
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import SystemSetting, ActivityLog
from .forms import SystemSettingForm
from .utils import get_dashboard_metrics, paginate_queryset
from products.models import Product, ProductVariant
from plans.models import SubscriptionPlan
from subscriptions.models import Customer, Subscription

class DashboardView(View):
    """Admin Dashboard for Brightloop SaaS."""
    template_name = 'dashboard/index.html'

    def get(self, request):
        metrics = get_dashboard_metrics()
        
        # Recent records for overview tables
        recent_products = Product.objects.select_related('category').prefetch_related('plans')[:5]
        recent_plans = SubscriptionPlan.objects.select_related('product')[:5]
        recent_subscriptions = Subscription.objects.select_related('customer', 'plan')[:6]
        recent_activities = ActivityLog.objects.all()[:8]

        context = {
            'metrics': metrics,
            'recent_products': recent_products,
            'recent_plans': recent_plans,
            'recent_subscriptions': recent_subscriptions,
            'recent_activities': recent_activities,
            # JSON chart payloads
            'chart_revenue_json': json.dumps(metrics['chart_revenue']),
            'chart_plans_json': json.dumps(metrics['chart_plans']),
            'chart_status_json': json.dumps(metrics['chart_status']),
            'page_title': 'Admin Executive Dashboard',
        }
        return render(request, self.template_name, context)


class AdminSettingsView(View):
    """Admin Settings view allowing live reconfiguration."""
    template_name = 'settings/admin_settings.html'

    def get(self, request):
        settings_obj = SystemSetting.get_settings()
        form = SystemSettingForm(instance=settings_obj)
        context = {
            'form': form,
            'settings_obj': settings_obj,
            'page_title': 'System & Administrative Settings',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        settings_obj = SystemSetting.get_settings()
        form = SystemSettingForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                action="Updated system configuration and billing parameters",
                category="setting",
                user=request.user if request.user.is_authenticated else None,
                details=f"Company: {settings_obj.company_name}, Currency: {settings_obj.currency_symbol}"
            )
            messages.success(request, "System settings have been successfully updated.")
            return redirect('admin_settings')
        
        messages.error(request, "Please correct the errors indicated below.")
        context = {
            'form': form,
            'settings_obj': settings_obj,
            'page_title': 'System & Administrative Settings',
        }
        return render(request, self.template_name, context)


class ExportCenterView(View):
    """Data Export Hub for SaaS entities."""
    template_name = 'exports/export_center.html'

    def get(self, request):
        context = {
            'page_title': 'Data Export & Reporting Interface',
            'products_count': Product.objects.count(),
            'variants_count': ProductVariant.objects.count(),
            'plans_count': SubscriptionPlan.objects.count(),
            'subscriptions_count': Subscription.objects.count(),
            'customers_count': Customer.objects.count(),
        }
        return render(request, self.template_name, context)


class ExportDownloadView(View):
    """Generates and serves downloadable CSV / JSON datasets."""
    def get(self, request):
        entity = request.GET.get('entity', 'products')
        file_format = request.GET.get('format', 'csv')
        date_filter = request.GET.get('date_range', 'all')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        # Log action
        ActivityLog.objects.create(
            action=f"Exported {entity.upper()} data ({file_format.upper()})",
            category="export",
            user=request.user if request.user.is_authenticated else None,
            details=f"Entity: {entity}, Format: {file_format}, Range: {date_filter}"
        )

        if entity == 'products':
            return self._export_products(file_format, timestamp)
        elif entity == 'variants':
            return self._export_variants(file_format, timestamp)
        elif entity == 'plans':
            return self._export_plans(file_format, timestamp)
        elif entity == 'subscriptions':
            return self._export_subscriptions(file_format, timestamp)
        elif entity == 'customers':
            return self._export_customers(file_format, timestamp)
        else:
            messages.error(request, "Invalid export entity specified.")
            return redirect('export_center')

    def _export_products(self, file_format, timestamp):
        qs = Product.objects.select_related('category').all()
        if file_format == 'json':
            data = [
                {
                    'id': p.id,
                    'sku': p.sku,
                    'name': p.name,
                    'category': p.category.name if p.category else None,
                    'status': p.status,
                    'base_price': float(p.base_price),
                    'is_featured': p.is_featured,
                    'created_at': p.created_at.isoformat(),
                } for p in qs
            ]
            response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="brightloop_products_{timestamp}.json"'
            return response
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="brightloop_products_{timestamp}.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'SKU', 'Product Name', 'Category', 'Status', 'Base Price', 'Featured', 'Created At'])
            for p in qs:
                writer.writerow([
                    p.id, p.sku, p.name,
                    p.category.name if p.category else '',
                    p.status, p.base_price, p.is_featured,
                    p.created_at.strftime('%Y-%m-%d %H:%M')
                ])
            return response

    def _export_variants(self, file_format, timestamp):
        qs = ProductVariant.objects.select_related('product').all()
        if file_format == 'json':
            data = [
                {
                    'id': v.id,
                    'product': v.product.name,
                    'sku': v.sku,
                    'variant_name': v.name,
                    'tier': v.tier,
                    'billing_cycle': v.billing_cycle,
                    'price': float(v.price),
                    'max_users': v.max_users,
                    'storage_gb': v.storage_gb,
                    'is_active': v.is_active,
                } for v in qs
            ]
            response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="brightloop_variants_{timestamp}.json"'
            return response
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="brightloop_variants_{timestamp}.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Product', 'Variant SKU', 'Variant Name', 'Tier', 'Billing Cycle', 'Price', 'Max Users', 'Storage (GB)', 'Active'])
            for v in qs:
                writer.writerow([
                    v.id, v.product.name, v.sku, v.name, v.tier, v.billing_cycle,
                    v.price, v.max_users, v.storage_gb, v.is_active
                ])
            return response

    def _export_plans(self, file_format, timestamp):
        qs = SubscriptionPlan.objects.select_related('product', 'variant').all()
        if file_format == 'json':
            data = [
                {
                    'id': p.id,
                    'code': p.code,
                    'name': p.name,
                    'product': p.product.name,
                    'variant': p.variant.name if p.variant else None,
                    'tier': p.tier,
                    'billing_cycle': p.billing_cycle,
                    'price': float(p.price),
                    'trial_days': p.trial_days,
                    'status': p.status,
                    'is_featured': p.is_featured,
                } for p in qs
            ]
            response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="brightloop_plans_{timestamp}.json"'
            return response
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="brightloop_plans_{timestamp}.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Plan Code', 'Plan Name', 'Product', 'Variant', 'Tier', 'Billing Cycle', 'Price', 'Trial Days', 'Status', 'Featured'])
            for p in qs:
                writer.writerow([
                    p.id, p.code, p.name, p.product.name,
                    p.variant.name if p.variant else '',
                    p.tier, p.billing_cycle, p.price, p.trial_days, p.status, p.is_featured
                ])
            return response

    def _export_subscriptions(self, file_format, timestamp):
        qs = Subscription.objects.select_related('customer', 'plan').all()
        if file_format == 'json':
            data = [
                {
                    'id': s.id,
                    'subscription_id': s.subscription_id,
                    'customer': s.customer.full_name,
                    'email': s.customer.email,
                    'plan': s.plan.name,
                    'status': s.status,
                    'amount': float(s.current_amount),
                    'start_date': s.start_date.isoformat(),
                    'next_billing_date': s.next_billing_date.isoformat(),
                } for s in qs
            ]
            response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="brightloop_subscriptions_{timestamp}.json"'
            return response
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="brightloop_subscriptions_{timestamp}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Subscription ID', 'Customer Name', 'Email', 'Plan', 'Status', 'Amount', 'Start Date', 'Next Billing Date'])
            for s in qs:
                writer.writerow([
                    s.subscription_id, s.customer.full_name, s.customer.email,
                    s.plan.name, s.status, s.current_amount,
                    s.start_date, s.next_billing_date
                ])
            return response

    def _export_customers(self, file_format, timestamp):
        qs = Customer.objects.all()
        if file_format == 'json':
            data = [
                {
                    'id': c.id,
                    'name': c.full_name,
                    'company': c.company_name,
                    'email': c.email,
                    'phone': c.phone,
                    'country': c.country,
                    'status': c.status,
                    'joined_at': c.created_at.isoformat(),
                } for c in qs
            ]
            response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="brightloop_customers_{timestamp}.json"'
            return response
        else:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="brightloop_customers_{timestamp}.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Full Name', 'Company', 'Email', 'Phone', 'Country', 'Status', 'Joined Date'])
            for c in qs:
                writer.writerow([
                    c.id, c.full_name, c.company_name, c.email, c.phone, c.country, c.status,
                    c.created_at.strftime('%Y-%m-%d')
                ])
            return response
