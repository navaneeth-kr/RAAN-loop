import csv
import json
from datetime import datetime, date
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q, Count
from django.utils import timezone
from .models import SystemSetting, ActivityLog, StaffProfile
from .forms import SystemSettingForm
from .utils import get_dashboard_metrics, paginate_queryset
from products.models import Product, ProductVariant
from plans.models import SubscriptionPlan
from subscriptions.models import Customer, Subscription, Invoice, Payment, Quotation, Discount

class AdminRequiredMixin(UserPassesTestMixin):
    """Restricts access to staff or superuser admins."""
    login_url = '/login/'

    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.is_superuser)

    def handle_no_permission(self):
        messages.warning(self.request, "Administrator privileges required. Please sign in with an admin account.")
        return redirect(f"{self.login_url}?next={self.request.path}")


class AdminLoginView(View):
    """Admin sign-in portal with quick demo access."""
    template_name = 'auth/login.html'

    def get(self, request):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return redirect('dashboard')
        return render(request, self.template_name, {'next': request.GET.get('next', '/')})

    def post(self, request):
        # Quick 1-click Demo Login handler
        if 'demo_admin' in request.POST:
            admin_user = User.objects.filter(is_staff=True).first()
            if admin_user:
                login(request, admin_user)
                messages.success(request, f"Welcome back, {admin_user.get_full_name() or admin_user.username} (Administrator).")
                return redirect(request.POST.get('next') or 'dashboard')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user is not None and (user.is_staff or user.is_superuser):
            login(request, user)
            ActivityLog.objects.create(
                action=f"Admin {user.username} logged in",
                category="system",
                user=user
            )
            messages.success(request, f"Signed in successfully as {user.username}.")
            next_url = request.POST.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Invalid administrator credentials or access denied.")
            return render(request, self.template_name, {'username': username, 'next': request.POST.get('next', '/')})


class AdminLogoutView(View):
    """Admin sign-out handler."""
    def get(self, request):
        logout(request)
        messages.info(request, "You have been securely signed out.")
        return redirect('admin_login')


class DashboardView(AdminRequiredMixin, View):
    """Executive Admin Dashboard with the 6 primary KPI cards and real DB metrics."""
    template_name = 'dashboard/index.html'

    def get(self, request):
        # Date filtering & search
        search_query = request.GET.get('q', '').strip()
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        metrics = get_dashboard_metrics(start_date=start_date, end_date=end_date, search_query=search_query)

        context = {
            'metrics': metrics,
            'recent_subscriptions': metrics['recent_subscriptions'],
            'recent_payments': metrics['recent_payments'],
            'overdue_invoice_list': metrics['overdue_invoice_list'],
            'search_query': search_query,
            'start_date': start_date_str,
            'end_date': end_date_str,
            # JSON chart payloads
            'chart_revenue_json': json.dumps(metrics['chart_revenue']),
            'chart_status_json': json.dumps(metrics['chart_status']),
            'page_title': 'Executive Admin Dashboard',
        }
        return render(request, self.template_name, context)


class StaffListView(AdminRequiredMixin, View):
    """List staff members and permission roles."""
    template_name = 'staff/staff_list.html'

    def get(self, request):
        staff_members = User.objects.filter(is_staff=True).select_related('staff_profile').order_by('-date_joined')
        context = {
            'staff_members': staff_members,
            'page_title': 'Staff & Role Management',
        }
        return render(request, self.template_name, context)


class ReportsView(AdminRequiredMixin, View):
    """Date-based reporting interface with dynamic analytics."""
    template_name = 'reports/reports.html'

    def get(self, request):
        today = timezone.now().date()
        range_preset = request.GET.get('preset', '30d')
        
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        if range_preset == '7d':
            start_date = today - timezone.timedelta(days=7)
            end_date = today
        elif range_preset == '90d':
            start_date = today - timezone.timedelta(days=90)
            end_date = today
        elif range_preset == '1y':
            start_date = today - timezone.timedelta(days=365)
            end_date = today
        elif start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = today - timezone.timedelta(days=30)
                end_date = today
        else:
            start_date = today - timezone.timedelta(days=30)
            end_date = today

        # Compute period reports
        payments_in_period = Payment.objects.filter(status='completed', payment_date__date__gte=start_date, payment_date__date__lte=end_date)
        period_revenue = payments_in_period.aggregate(total=Sum('amount'))['total'] or 0.00
        new_subscriptions_count = Subscription.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).count()
        invoices_issued = Invoice.objects.filter(issued_date__gte=start_date, issued_date__lte=end_date).count()

        context = {
            'start_date': start_date,
            'end_date': end_date,
            'range_preset': range_preset,
            'period_revenue': period_revenue,
            'new_subscriptions_count': new_subscriptions_count,
            'invoices_issued': invoices_issued,
            'payments_in_period': payments_in_period[:15],
            'page_title': 'Date-Based Financial & Operational Reports',
        }
        return render(request, self.template_name, context)


class AdminSettingsView(AdminRequiredMixin, View):
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
                user=request.user,
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


class ExportCenterView(AdminRequiredMixin, View):
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


class ExportDownloadView(AdminRequiredMixin, View):
    """Generates and serves downloadable CSV / JSON datasets across all entities."""
    def get(self, request):
        entity = request.GET.get('entity', 'products').lower()
        file_format = request.GET.get('format', 'csv').lower()
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        ActivityLog.objects.create(
            action=f"Exported {entity.upper()} data ({file_format.upper()})",
            category="export",
            user=request.user,
            details=f"Entity: {entity}, Format: {file_format}"
        )

        headers = []
        rows = []
        json_data = []

        if entity == 'products':
            headers = ['ID', 'SKU', 'Name', 'Product Type', 'Category', 'Selling Price', 'Cost Price', 'Gross Profit', 'Status', 'Created At']
            qs = Product.objects.select_related('category').all()
            for p in qs:
                row = [
                    p.id, p.sku, p.name, p.get_product_type_display(),
                    p.category.name if p.category else '',
                    float(p.selling_price), float(p.cost_price), float(p.gross_profit),
                    p.status, p.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ]
                rows.append(row)
                json_data.append({
                    'id': p.id, 'sku': p.sku, 'name': p.name, 'product_type': p.product_type,
                    'category': p.category.name if p.category else None,
                    'selling_price': float(p.selling_price), 'cost_price': float(p.cost_price),
                    'gross_profit': float(p.gross_profit), 'status': p.status,
                    'created_at': str(p.created_at)
                })

        elif entity == 'variants':
            headers = ['ID', 'Product', 'Variant Name', 'Tier', 'Additional Charge', 'Final Price', 'Billing Cycle', 'Active']
            qs = ProductVariant.objects.select_related('product').all()
            for v in qs:
                row = [
                    v.id, v.product.name, v.name, v.get_tier_display(),
                    float(v.additional_charge), float(v.final_price),
                    v.billing_cycle, 'Yes' if v.is_active else 'No'
                ]
                rows.append(row)
                json_data.append({
                    'id': v.id, 'product': v.product.name, 'name': v.name, 'tier': v.tier,
                    'additional_charge': float(v.additional_charge), 'final_price': float(v.final_price),
                    'billing_cycle': v.billing_cycle, 'is_active': v.is_active
                })

        elif entity == 'plans':
            headers = ['ID', 'Plan Code', 'Plan Name', 'Product', 'Variant', 'Billing Frequency', 'Price', 'Min Quantity', 'Auto Close', 'Early Cancellation', 'Pausing', 'Renewal', 'Status', 'Start Date', 'End Date']
            qs = SubscriptionPlan.objects.select_related('product', 'variant').all()
            for pl in qs:
                row = [
                    pl.id, pl.code, pl.name, pl.product.name if pl.product else '',
                    pl.variant.name if pl.variant else '',
                    pl.billing_frequency, float(pl.price), pl.min_quantity,
                    'Yes' if pl.auto_close else 'No',
                    'Yes' if pl.allow_early_cancellation else 'No',
                    'Yes' if pl.allow_pausing else 'No',
                    'Yes' if pl.allow_renewal else 'No',
                    pl.status,
                    pl.start_date.strftime('%Y-%m-%d') if pl.start_date else '',
                    pl.end_date.strftime('%Y-%m-%d') if pl.end_date else ''
                ]
                rows.append(row)
                json_data.append({
                    'id': pl.id, 'code': pl.code, 'name': pl.name,
                    'product': pl.product.name if pl.product else None,
                    'variant': pl.variant.name if pl.variant else None,
                    'billing_frequency': pl.billing_frequency,
                    'price': float(pl.price), 'min_quantity': pl.min_quantity,
                    'auto_close': pl.auto_close, 'allow_early_cancellation': pl.allow_early_cancellation,
                    'allow_pausing': pl.allow_pausing, 'allow_renewal': pl.allow_renewal,
                    'status': pl.status,
                    'start_date': str(pl.start_date) if pl.start_date else None,
                    'end_date': str(pl.end_date) if pl.end_date else None,
                })

        elif entity == 'subscriptions':
            headers = ['ID', 'Customer', 'Plan', 'Amount', 'Status', 'Renewal Date', 'Created At']
            qs = Subscription.objects.select_related('customer', 'plan').all()
            for s in qs:
                row = [
                    s.subscription_id, s.customer.full_name, s.plan.name if s.plan else '',
                    float(s.current_amount), s.status,
                    s.next_billing_date.strftime('%Y-%m-%d') if s.next_billing_date else '',
                    s.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(s, 'created_at') and s.created_at else ''
                ]
                rows.append(row)
                json_data.append({
                    'subscription_id': s.subscription_id, 'customer': s.customer.full_name,
                    'plan': s.plan.name if s.plan else None, 'amount': float(s.current_amount),
                    'status': s.status, 'next_billing_date': str(s.next_billing_date) if s.next_billing_date else None
                })

        elif entity == 'customers':
            headers = ['Customer ID', 'Full Name', 'Email', 'Company', 'Status', 'Created At']
            qs = Customer.objects.all()
            for c in qs:
                row = [
                    c.customer_id, c.full_name, c.email, c.company_name or '',
                    c.status, c.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(c, 'created_at') and c.created_at else ''
                ]
                rows.append(row)
                json_data.append({
                    'customer_id': c.customer_id, 'full_name': c.full_name, 'email': c.email,
                    'company_name': c.company_name, 'status': c.status
                })

        else:
            messages.warning(request, f"Unknown entity '{entity}' requested for export.")
            return redirect('export_center')

        if file_format == 'json':
            response = HttpResponse(json.dumps(json_data, indent=2, default=str), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="brightloop_{entity}_{timestamp}.json"'
            return response
        else:
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="brightloop_{entity}_{timestamp}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response

