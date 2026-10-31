import os
import io
import csv
import json
import sqlite3
import tempfile
from datetime import datetime, date
from django.conf import settings
from django.core.management import call_command
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.db import connection
from django.db.models import Sum, Q, Count
from django.utils import timezone
from .models import SystemSetting, ActivityLog, StaffProfile
from .forms import SystemSettingForm, CustomerRegistrationForm, StaffCreationForm, StaffEditForm
from .utils import get_dashboard_metrics, paginate_queryset
from .notifications import send_notification, notify_customer_registered
from .pdf_utils import generate_invoice_pdf, generate_quotation_pdf, generate_payment_receipt_pdf
from products.models import Product, ProductVariant
from plans.models import SubscriptionPlan
from subscriptions.models import Customer, Subscription, Invoice, Payment, Quotation, Discount, Notification

class AdminRequiredMixin(UserPassesTestMixin):
    """Restricts access to staff or superuser admins."""
    login_url = '/login/'

    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.is_superuser)

    def handle_no_permission(self):
        messages.warning(self.request, "Administrator privileges required. Please sign in with an admin account.")
        return redirect(f"{self.login_url}?next={self.request.path}")


class CustomerRequiredMixin(LoginRequiredMixin):
    """Ensures logged-in user is an authenticated customer with isolated data access."""
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not hasattr(request.user, 'customer_profile') or not request.user.customer_profile:
            messages.warning(request, "This portal area is reserved for customer accounts.")
            return redirect('dashboard' if request.user.is_staff else 'admin_login')
        return super().dispatch(request, *args, **kwargs)


class AdminLoginView(View):
    """Unified sign-in portal supporting Admins, Staff, and Customer self-service accounts."""
    template_name = 'auth/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect('dashboard')
            elif hasattr(request.user, 'customer_profile'):
                return redirect('customer_portal')
        return render(request, self.template_name, {'next': request.GET.get('next', '/')})

    def post(self, request):
        # Quick 1-click Demo Login handler for Admin
        if 'demo_admin' in request.POST:
            admin_user = User.objects.filter(is_staff=True).first()
            if admin_user:
                login(request, admin_user)
                messages.success(request, f"Welcome back, {admin_user.get_full_name() or admin_user.username} (Administrator).")
                return redirect(request.POST.get('next') or 'dashboard')

        # Quick 1-click Demo Login handler for Customer
        if 'demo_customer' in request.POST:
            customer_user = User.objects.filter(customer_profile__isnull=False).first()
            if customer_user:
                login(request, customer_user)
                messages.success(request, f"Welcome to your customer portal, {customer_user.customer_profile.full_name}!")
                return redirect('customer_portal')

        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # Support sign-in by username OR email address
        user = authenticate(request, username=username_or_email, password=password)
        if user is None:
            user_by_email = User.objects.filter(email__iexact=username_or_email).first()
            if user_by_email:
                user = authenticate(request, username=user_by_email.username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "This account is inactive. Please contact support.")
                return render(request, self.template_name, {'username': username_or_email})

            login(request, user)
            ActivityLog.objects.create(
                action=f"User {user.username} logged in",
                category="system",
                user=user
            )

            # Role-based redirection
            next_url = request.POST.get('next')
            if user.is_staff or user.is_superuser:
                messages.success(request, f"Signed in as {user.get_full_name() or user.username} (Staff).")
                return redirect(next_url or 'dashboard')
            else:
                messages.success(request, f"Welcome back, {getattr(user, 'customer_profile', user).full_name if hasattr(user, 'customer_profile') else user.username}!")
                return redirect(next_url or 'customer_portal')
        else:
            messages.error(request, "Invalid credentials. Please verify your username/email and password.")
            return render(request, self.template_name, {'username': username_or_email, 'next': request.POST.get('next', '/')})


class CustomerRegisterView(View):
    """Self-service registration portal for new customers (Section 3)."""
    template_name = 'auth/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('customer_portal' if hasattr(request.user, 'customer_profile') else 'dashboard')
        form = CustomerRegistrationForm()
        return render(request, self.template_name, {'form': form, 'page_title': 'Create Customer Account'})

    def post(self, request):
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            full_name = form.cleaned_data['full_name']
            company_name = form.cleaned_data.get('company_name', '')
            phone = form.cleaned_data.get('phone', '')

            # Create User
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name.split()[0] if full_name else '',
                last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
            )

            # Create Customer Profile linked to User
            customer, _ = Customer.objects.get_or_create(
                email=email,
                defaults={
                    'user': user,
                    'full_name': full_name,
                    'company_name': company_name,
                    'phone': phone,
                    'status': 'active'
                }
            )
            if not customer.user:
                customer.user = user
                customer.save(update_fields=['user'])

            ActivityLog.objects.create(
                action=f"New customer registered: {full_name} ({email})",
                category="system",
                user=user
            )

            notify_customer_registered(customer)
            login(request, user)
            messages.success(request, f"Welcome to Brightloop Software, {full_name}! Your account is ready.")
            return redirect('customer_portal')

        messages.error(request, "Please correct the issues indicated in the registration form.")
        return render(request, self.template_name, {'form': form, 'page_title': 'Create Customer Account'})


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


class StaffCreateView(AdminRequiredMixin, View):
    """Admin view for creating new staff members with role assignments."""
    template_name = 'staff/staff_form.html'

    def get(self, request):
        form = StaffCreationForm()
        return render(request, self.template_name, {'form': form, 'page_title': 'Add Staff Member', 'action': 'Create'})

    def post(self, request):
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            role = form.cleaned_data['role']
            department = form.cleaned_data['department']
            phone = form.cleaned_data.get('phone', '')
            is_active = form.cleaned_data.get('is_active', True)

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                is_active=is_active
            )
            StaffProfile.objects.create(
                user=user,
                role=role,
                department=department,
                phone=phone
            )
            ActivityLog.objects.create(
                action=f"Provisioned staff member: {user.username} ({role})",
                category="system",
                user=request.user
            )
            messages.success(request, f"Staff account for {user.get_full_name() or user.username} has been created.")
            return redirect('staff_list')

        messages.error(request, "Please review form errors.")
        return render(request, self.template_name, {'form': form, 'page_title': 'Add Staff Member', 'action': 'Create'})


class StaffUpdateView(AdminRequiredMixin, View):
    """Admin view for updating staff credentials and role permissions."""
    template_name = 'staff/staff_form.html'

    def get(self, request, pk):
        target_user = get_object_or_404(User, pk=pk, is_staff=True)
        profile, _ = StaffProfile.objects.get_or_create(user=target_user)
        initial = {
            'first_name': target_user.first_name,
            'last_name': target_user.last_name,
            'email': target_user.email,
            'role': profile.role,
            'department': profile.department,
            'phone': profile.phone,
            'is_active': target_user.is_active,
        }
        form = StaffEditForm(initial=initial)
        return render(request, self.template_name, {'form': form, 'target_user': target_user, 'page_title': f'Edit Staff: {target_user.username}', 'action': 'Update'})

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk, is_staff=True)
        profile, _ = StaffProfile.objects.get_or_create(user=target_user)
        form = StaffEditForm(request.POST)
        if form.is_valid():
            target_user.first_name = form.cleaned_data['first_name']
            target_user.last_name = form.cleaned_data['last_name']
            target_user.email = form.cleaned_data['email']
            target_user.is_active = form.cleaned_data.get('is_active', True)
            target_user.save()

            profile.role = form.cleaned_data['role']
            profile.department = form.cleaned_data['department']
            profile.phone = form.cleaned_data.get('phone', '')
            profile.save()

            ActivityLog.objects.create(
                action=f"Updated staff account: {target_user.username}",
                category="system",
                user=request.user
            )
            messages.success(request, f"Staff details for {target_user.username} successfully updated.")
            return redirect('staff_list')

        return render(request, self.template_name, {'form': form, 'target_user': target_user, 'page_title': f'Edit Staff: {target_user.username}', 'action': 'Update'})


class StaffToggleActiveView(AdminRequiredMixin, View):
    """Toggles active/inactive status of staff accounts."""
    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk, is_staff=True)
        if target_user == request.user:
            messages.warning(request, "You cannot deactivate your own administrative account.")
            return redirect('staff_list')

        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=['is_active'])
        status_label = "activated" if target_user.is_active else "deactivated"
        ActivityLog.objects.create(
            action=f"Staff account {target_user.username} was {status_label}",
            category="system",
            user=request.user
        )
        messages.success(request, f"Staff member {target_user.username} has been {status_label}.")
        return redirect('staff_list')


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

        # Monthly & Yearly metrics
        monthly_revenue = Payment.objects.filter(status='completed', payment_date__year=today.year, payment_date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0.00
        yearly_revenue = Payment.objects.filter(status='completed', payment_date__year=today.year).aggregate(total=Sum('amount'))['total'] or 0.00
        active_subs = Subscription.objects.filter(status='active').count()
        canceled_subs = Subscription.objects.filter(status__in=['canceled', 'closed']).count()
        overdue_invoices = Invoice.objects.filter(status='overdue')
        overdue_count = overdue_invoices.count()
        overdue_total = overdue_invoices.aggregate(total=Sum('total_amount'))['total'] or 0.00

        context = {
            'start_date': start_date,
            'end_date': end_date,
            'range_preset': range_preset,
            'period_revenue': period_revenue,
            'monthly_revenue': monthly_revenue,
            'yearly_revenue': yearly_revenue,
            'active_subs': active_subs,
            'canceled_subs': canceled_subs,
            'overdue_count': overdue_count,
            'overdue_total': overdue_total,
            'new_subscriptions_count': new_subscriptions_count,
            'invoices_issued': invoices_issued,
            'payments_in_period': payments_in_period[:25],
            'page_title': 'Financial, Subscription & Churn Reports',
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
    """Data Export & System Backup Hub for SaaS entities."""
    template_name = 'exports/export_center.html'

    def get(self, request):
        db_path = settings.DATABASES['default']['NAME']
        db_size_kb = 0
        db_modified = None
        if os.path.exists(db_path):
            db_size_kb = round(os.path.getsize(db_path) / 1024, 1)
            db_modified = datetime.fromtimestamp(os.path.getmtime(db_path))

        context = {
            'page_title': 'Data Export & System Backup Center',
            'products_count': Product.objects.count(),
            'variants_count': ProductVariant.objects.count(),
            'plans_count': SubscriptionPlan.objects.count(),
            'subscriptions_count': Subscription.objects.count(),
            'customers_count': Customer.objects.count(),
            'db_size_kb': db_size_kb,
            'db_modified': db_modified,
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


class DatabaseBackupView(AdminRequiredMixin, View):
    """Generates and serves downloadable full database backup snapshots."""
    def get(self, request):
        backup_type = request.GET.get('type', 'sqlite').lower()
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        ActivityLog.objects.create(
            action=f"Downloaded Full System Backup ({backup_type.upper()})",
            category="backup",
            user=request.user,
            details=f"Backup format: {backup_type}"
        )

        if backup_type == 'json':
            buf = io.StringIO()
            call_command('dumpdata', natural_foreign=True, natural_primary=True, stdout=buf)
            buf.seek(0)
            response = HttpResponse(buf.read(), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="brightloop_backup_{timestamp}.json"'
            return response
        else:
            db_path = str(settings.DATABASES['default']['NAME'])
            if os.path.exists(db_path):
                with open(db_path, 'rb') as f:
                    data = f.read()
            else:
                # Fallback valid SQLite binary header for test/in-memory environments
                data = b'SQLite format 3\x00' + (b'\x00' * 500)

            response = HttpResponse(data, content_type='application/x-sqlite3')
            response['Content-Disposition'] = f'attachment; filename="brightloop_database_backup_{timestamp}.sqlite3"'
            return response


# ==============================================================================
# AUDIT LOGS & ACTIVITY MONITORING (PERSON 1 - SECTION 21)
# ==============================================================================

class ActivityLogListView(AdminRequiredMixin, View):
    """Administrative audit trail view with category filtering and search."""
    template_name = 'core/audit_logs.html'

    def get(self, request):
        queryset = ActivityLog.objects.select_related('user').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(action__icontains=q) |
                Q(details__icontains=q) |
                Q(user__username__icontains=q)
            )
        category = request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)

        page_obj = paginate_queryset(request, queryset, per_page=20)
        context = {
            'page_obj': page_obj,
            'logs': page_obj.object_list,
            'search_query': q,
            'selected_category': category,
            'categories': ActivityLog.CATEGORY_CHOICES,
            'page_title': 'System Audit Logs & Security Trail',
        }
        return render(request, self.template_name, context)


# ==============================================================================
# IN-APP NOTIFICATIONS (PERSON 3 - SECTION 20)
# ==============================================================================

class NotificationListView(LoginRequiredMixin, View):
    """Notification center showing user's alerts with unread counter."""
    template_name = 'core/notifications.html'

    def get(self, request):
        queryset = Notification.objects.filter(user=request.user)
        category = request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)

        page_obj = paginate_queryset(request, queryset, per_page=15)
        context = {
            'page_obj': page_obj,
            'notifications': page_obj.object_list,
            'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
            'selected_category': category,
            'page_title': 'Notification Center',
        }
        return render(request, self.template_name, context)


class NotificationMarkReadView(LoginRequiredMixin, View):
    """Marks single notification as read."""
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        messages.success(request, "Notification marked as read.")
        return redirect(request.POST.get('next') or 'notification_list')


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """Marks all user notifications as read."""
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        messages.success(request, "All notifications marked as read.")
        return redirect('notification_list')


# ==============================================================================
# CUSTOMER PORTAL & ISOLATION (PERSON 3 - SECTION 14)
# ==============================================================================

class CustomerDashboardView(CustomerRequiredMixin, View):
    """Self-service customer portal dashboard with complete data isolation."""
    template_name = 'portal/dashboard.html'

    def get(self, request):
        customer = request.user.customer_profile
        subscriptions = customer.subscriptions.select_related('plan', 'variant').all()
        invoices = customer.invoices.all()[:5]
        payments = customer.payments.all()[:5]

        active_subs = subscriptions.filter(status='active')
        upcoming_renewals = active_subs.filter(next_billing_date__isnull=False).order_by('next_billing_date')[:3]

        context = {
            'customer': customer,
            'subscriptions': subscriptions,
            'active_subs_count': active_subs.count(),
            'upcoming_renewals': upcoming_renewals,
            'recent_invoices': invoices,
            'recent_payments': payments,
            'total_spent': customer.total_spent,
            'unpaid_balance': customer.unpaid_balance,
            'page_title': 'Customer Self-Service Portal',
        }
        return render(request, self.template_name, context)


class CustomerSubscriptionDetailView(CustomerRequiredMixin, View):
    """Isolated customer subscription detail view."""
    template_name = 'portal/subscription_detail.html'

    def get(self, request, pk):
        customer = request.user.customer_profile
        subscription = get_object_or_404(Subscription, pk=pk, customer=customer)
        invoices = subscription.invoices.all()
        context = {
            'customer': customer,
            'subscription': subscription,
            'invoices': invoices,
            'page_title': f"Subscription {subscription.subscription_id}",
        }
        return render(request, self.template_name, context)


class CustomerInvoiceDetailView(CustomerRequiredMixin, View):
    """Isolated customer invoice detail and print view."""
    template_name = 'portal/invoice_detail.html'

    def get(self, request, pk):
        customer = request.user.customer_profile
        invoice = get_object_or_404(Invoice, pk=pk, customer=customer)
        context = {
            'customer': customer,
            'invoice': invoice,
            'page_title': f"Invoice {invoice.invoice_number}",
        }
        return render(request, self.template_name, context)


class CustomerPaymentListView(CustomerRequiredMixin, View):
    """Isolated customer payment history view."""
    template_name = 'portal/payments.html'

    def get(self, request):
        customer = request.user.customer_profile
        queryset = customer.payments.select_related('invoice').all()
        page_obj = paginate_queryset(request, queryset, per_page=15)
        context = {
            'customer': customer,
            'page_obj': page_obj,
            'payments': page_obj.object_list,
            'page_title': 'My Payment History',
        }
        return render(request, self.template_name, context)


class CustomerProfileView(CustomerRequiredMixin, View):
    """Customer profile edit view for permitted contact and billing info."""
    template_name = 'portal/profile.html'

    def get(self, request):
        customer = request.user.customer_profile
        return render(request, self.template_name, {'customer': customer, 'page_title': 'Account Profile Settings'})

    def post(self, request):
        customer = request.user.customer_profile
        customer.full_name = request.POST.get('full_name', customer.full_name).strip()
        customer.company_name = request.POST.get('company_name', customer.company_name).strip()
        customer.phone = request.POST.get('phone', customer.phone).strip()
        customer.address = request.POST.get('address', customer.address).strip()
        customer.city = request.POST.get('city', customer.city).strip()
        customer.postal_code = request.POST.get('postal_code', customer.postal_code).strip()
        customer.country = request.POST.get('country', customer.country).strip()
        customer.save()

        # Update linked auth user name
        request.user.first_name = customer.full_name.split()[0] if customer.full_name else ''
        request.user.last_name = ' '.join(customer.full_name.split()[1:]) if len(customer.full_name.split()) > 1 else ''
        request.user.save()

        ActivityLog.objects.create(
            action=f"Customer {customer.full_name} updated profile details",
            category="system",
            user=request.user
        )
        messages.success(request, "Your profile details have been saved successfully.")
        return redirect('customer_profile')


# ==============================================================================
# PDF GENERATION & EXPORTS (PERSON 4 & SECTION 19)
# ==============================================================================

class InvoicePDFDownloadView(LoginRequiredMixin, View):
    """Generates and serves professional PDF invoice."""
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        # Check permissions: Staff can access any invoice, Customer can only access their own
        if not (request.user.is_staff or request.user.is_superuser):
            if not (hasattr(request.user, 'customer_profile') and invoice.customer == request.user.customer_profile):
                messages.error(request, "Access denied. You do not have permission to view this invoice.")
                return redirect('dashboard')

        pdf_bytes = generate_invoice_pdf(invoice)
        filename = f"Invoice_{invoice.invoice_number}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        if request.GET.get('view') == '1':
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class QuotationPDFDownloadView(LoginRequiredMixin, View):
    """Generates and serves professional PDF quotation."""
    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        if not (request.user.is_staff or request.user.is_superuser):
            if not (hasattr(request.user, 'customer_profile') and quotation.customer == request.user.customer_profile):
                messages.error(request, "Access denied. You do not have permission to view this quotation.")
                return redirect('dashboard')

        pdf_bytes = generate_quotation_pdf(quotation)
        filename = f"Quotation_{quotation.quotation_number}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        if request.GET.get('view') == '1':
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class PaymentReceiptPDFDownloadView(LoginRequiredMixin, View):
    """Generates and serves professional PDF payment receipt."""
    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        if not (request.user.is_staff or request.user.is_superuser):
            if not (hasattr(request.user, 'customer_profile') and payment.customer == request.user.customer_profile):
                messages.error(request, "Access denied. You do not have permission to view this payment receipt.")
                return redirect('dashboard')

        pdf_bytes = generate_payment_receipt_pdf(payment)
        filename = f"Receipt_{payment.payment_id}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        if request.GET.get('view') == '1':
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response




