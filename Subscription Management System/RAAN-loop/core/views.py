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
    """Generates and serves downloadable CSV / JSON datasets."""
    def get(self, request):
        entity = request.GET.get('entity', 'products')
        file_format = request.GET.get('format', 'csv')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        ActivityLog.objects.create(
            action=f"Exported {entity.upper()} data ({file_format.upper()})",
            category="export",
            user=request.user,
            details=f"Entity: {entity}, Format: {file_format}"
        )

        if entity == 'products':
            qs = Product.objects.select_related('category').all()
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="brightloop_products_{timestamp}.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'SKU', 'Name', 'Category', 'Base Price', 'Status', 'Created At'])
            for p in qs:
                writer.writerow([p.id, p.sku, p.name, p.category.name if p.category else '', p.base_price, p.status, p.created_at])
            return response
        elif entity == 'subscriptions':
            qs = Subscription.objects.select_related('customer', 'plan').all()
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="brightloop_subscriptions_{timestamp}.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Customer', 'Plan', 'Amount', 'Status', 'Renewal Date'])
            for s in qs:
                writer.writerow([s.subscription_id, s.customer.full_name, s.plan.name, s.current_amount, s.status, s.next_billing_date])
            return response
        else:
            return redirect('export_center')
