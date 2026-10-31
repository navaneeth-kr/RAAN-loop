import random
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.utils import timezone
from core.views import AdminRequiredMixin
from core.models import SystemSetting, ActivityLog
from core.utils import paginate_queryset
from .models import Customer, Subscription, Invoice, Payment, Quotation, Discount, TaxRate
from .forms import InvoiceForm, DiscountForm, PaymentForm, TaxRateForm, CustomerForm, SubscriptionForm, SubscriptionActionForm, QuotationForm
from core.notifications import notify_subscription_status, notify_invoice_generated, send_notification

# ==============================================================================
# 1. CUSTOMER MANAGEMENT VIEWS (PERSON 1 - SECTION 4)
# ==============================================================================

class CustomerListView(AdminRequiredMixin, View):
    """List and search customers with server-side filtering."""
    template_name = 'subscriptions/customer_list.html'

    def get(self, request):
        queryset = Customer.objects.all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(full_name__icontains=q) |
                Q(company_name__icontains=q) |
                Q(email__icontains=q) |
                Q(country__icontains=q)
            )
        status = request.GET.get('status')
        if status in ['active', 'inactive', 'suspended']:
            queryset = queryset.filter(status=status)

        page_obj = paginate_queryset(request, queryset, per_page=12)
        context = {
            'page_obj': page_obj,
            'customers': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'page_title': 'Customers Management',
        }
        return render(request, self.template_name, context)


class CustomerCreateView(AdminRequiredMixin, View):
    """Add new customer profile."""
    template_name = 'subscriptions/customer_form.html'

    def get(self, request):
        form = CustomerForm()
        return render(request, self.template_name, {'form': form, 'page_title': 'Add New Customer', 'action': 'Create'})

    def post(self, request):
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            ActivityLog.objects.create(
                action=f"Created customer account: {customer.full_name} ({customer.email})",
                category="customer",
                user=request.user
            )
            messages.success(request, f"Customer {customer.full_name} created successfully.")
            return redirect('customer_detail', pk=customer.pk)
        return render(request, self.template_name, {'form': form, 'page_title': 'Add New Customer', 'action': 'Create'})


class CustomerDetailView(AdminRequiredMixin, View):
    """360-degree Customer profile with tabbed history: Subscriptions, Invoices, Payments, Quotations."""
    template_name = 'subscriptions/customer_detail.html'

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        subscriptions = customer.subscriptions.select_related('plan', 'variant').all()
        invoices = customer.invoices.select_related('subscription').all()
        payments = customer.payments.select_related('invoice').all()
        quotations = customer.quotations.select_related('plan').all()

        context = {
            'customer': customer,
            'subscriptions': subscriptions,
            'invoices': invoices,
            'payments': payments,
            'quotations': quotations,
            'total_spent': customer.total_spent,
            'unpaid_balance': customer.unpaid_balance,
            'active_subs_count': customer.active_subscriptions_count,
            'page_title': f"Customer: {customer.full_name}",
        }
        return render(request, self.template_name, context)


class CustomerUpdateView(AdminRequiredMixin, View):
    """Update customer details."""
    template_name = 'subscriptions/customer_form.html'

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        form = CustomerForm(instance=customer)
        return render(request, self.template_name, {'form': form, 'customer': customer, 'page_title': f'Edit Customer: {customer.full_name}', 'action': 'Update'})

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            ActivityLog.objects.create(
                action=f"Updated customer profile: {customer.full_name}",
                category="customer",
                user=request.user
            )
            messages.success(request, f"Customer {customer.full_name} updated successfully.")
            return redirect('customer_detail', pk=customer.pk)
        return render(request, self.template_name, {'form': form, 'customer': customer, 'page_title': f'Edit Customer: {customer.full_name}', 'action': 'Update'})


class CustomerDeleteView(AdminRequiredMixin, View):
    """Delete customer account."""
    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        name = customer.full_name
        customer.delete()
        ActivityLog.objects.create(
            action=f"Deleted customer account: {name}",
            category="customer",
            user=request.user
        )
        messages.success(request, f"Customer {name} has been removed.")
        return redirect('customer_list')


# ==============================================================================
# 2. SUBSCRIPTION LIFECYCLE MANAGEMENT (PERSON 3 - SECTIONS 8 & 18)
# ==============================================================================

class SubscriptionListView(AdminRequiredMixin, View):
    """List customer subscriptions with search and status filtering."""
    template_name = 'subscriptions/subscription_list.html'

    def get(self, request):
        queryset = Subscription.objects.select_related('customer', 'plan', 'variant').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(subscription_id__icontains=q) |
                Q(customer__full_name__icontains=q) |
                Q(customer__email__icontains=q) |
                Q(plan__name__icontains=q)
            )
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        page_obj = paginate_queryset(request, queryset, per_page=12)
        context = {
            'page_obj': page_obj,
            'subscriptions': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'statuses': Subscription.STATUS_CHOICES,
            'page_title': 'Subscription Lifecycle Management',
        }
        return render(request, self.template_name, context)


class SubscriptionCreateView(AdminRequiredMixin, View):
    """Provision new subscription for a customer."""
    template_name = 'subscriptions/subscription_form.html'

    def get(self, request):
        initial = {}
        cust_id = request.GET.get('customer')
        if cust_id:
            cust = Customer.objects.filter(pk=cust_id).first()
            if cust:
                initial['customer'] = cust
        form = SubscriptionForm(initial=initial)
        return render(request, self.template_name, {'form': form, 'page_title': 'Provision New Subscription', 'action': 'Create'})

    def post(self, request):
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            sub = form.save()
            ActivityLog.objects.create(
                action=f"Provisioned subscription {sub.subscription_id} for {sub.customer.full_name}",
                category="subscription",
                user=request.user,
                details=f"Plan: {sub.plan.name}, Amount: ${sub.current_amount}"
            )
            notify_subscription_status(sub, "Provisioned & Created")
            messages.success(request, f"Subscription {sub.subscription_id} successfully created.")
            return redirect('subscription_detail', pk=sub.pk)
        return render(request, self.template_name, {'form': form, 'page_title': 'Provision New Subscription', 'action': 'Create'})


class SubscriptionDetailView(AdminRequiredMixin, View):
    """Subscription detail view showing lifecycle controls, billing schedule, and invoices."""
    template_name = 'subscriptions/subscription_detail.html'

    def get(self, request, pk):
        sub = get_object_or_404(Subscription.objects.select_related('customer', 'plan', 'variant'), pk=pk)
        invoices = sub.invoices.all().order_by('-issued_date')
        action_form = SubscriptionActionForm()
        context = {
            'sub': sub,
            'invoices': invoices,
            'action_form': action_form,
            'page_title': f"Subscription: {sub.subscription_id}",
        }
        return render(request, self.template_name, context)


class SubscriptionUpdateView(AdminRequiredMixin, View):
    """Edit subscription details."""
    template_name = 'subscriptions/subscription_form.html'

    def get(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        form = SubscriptionForm(instance=sub)
        return render(request, self.template_name, {'form': form, 'sub': sub, 'page_title': f'Edit Subscription: {sub.subscription_id}', 'action': 'Update'})

    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        form = SubscriptionForm(request.POST, instance=sub)
        if form.is_valid():
            sub = form.save()
            ActivityLog.objects.create(
                action=f"Updated subscription {sub.subscription_id}",
                category="subscription",
                user=request.user
            )
            messages.success(request, f"Subscription {sub.subscription_id} updated successfully.")
            return redirect('subscription_detail', pk=sub.pk)
        return render(request, self.template_name, {'form': form, 'sub': sub, 'page_title': f'Edit Subscription: {sub.subscription_id}', 'action': 'Update'})


class SubscriptionConfirmView(AdminRequiredMixin, View):
    """Confirms draft or quote-stage subscription."""
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        sub.status = 'confirmed'
        sub.save(update_fields=['status'])
        ActivityLog.objects.create(
            action=f"Subscription {sub.subscription_id} confirmed",
            category="subscription",
            user=request.user
        )
        notify_subscription_status(sub, "Confirmed")
        messages.success(request, f"Subscription {sub.subscription_id} has been confirmed.")
        return redirect('subscription_detail', pk=sub.pk)


class SubscriptionActivateView(AdminRequiredMixin, View):
    """Activates confirmed subscription."""
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        sub.status = 'active'
        sub.save(update_fields=['status'])
        ActivityLog.objects.create(
            action=f"Subscription {sub.subscription_id} activated",
            category="subscription",
            user=request.user
        )
        notify_subscription_status(sub, "Activated")
        messages.success(request, f"Subscription {sub.subscription_id} is now Active.")
        return redirect('subscription_detail', pk=sub.pk)


class SubscriptionPauseView(AdminRequiredMixin, View):
    """Pauses an active subscription if plan allows pausing."""
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        if not sub.can_pause:
            messages.error(request, f"Plan '{sub.plan.name}' does not permit subscription pausing.")
            return redirect('subscription_detail', pk=sub.pk)

        reason = request.POST.get('reason', '').strip()
        sub.status = 'paused'
        sub.paused_at = timezone.now()
        sub.cancellation_reason = reason
        sub.save(update_fields=['status', 'paused_at', 'cancellation_reason'])

        ActivityLog.objects.create(
            action=f"Subscription {sub.subscription_id} paused",
            category="subscription",
            user=request.user,
            details=f"Reason: {reason}"
        )
        notify_subscription_status(sub, "Paused", reason)
        messages.warning(request, f"Subscription {sub.subscription_id} has been paused.")
        return redirect('subscription_detail', pk=sub.pk)


class SubscriptionResumeView(AdminRequiredMixin, View):
    """Resumes a paused subscription."""
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        sub.status = 'active'
        sub.paused_at = None
        sub.save(update_fields=['status', 'paused_at'])

        ActivityLog.objects.create(
            action=f"Subscription {sub.subscription_id} resumed",
            category="subscription",
            user=request.user
        )
        notify_subscription_status(sub, "Resumed")
        messages.success(request, f"Subscription {sub.subscription_id} has been resumed to Active.")
        return redirect('subscription_detail', pk=sub.pk)


class SubscriptionCancelView(AdminRequiredMixin, View):
    """Cancels or closes subscription early with mandatory reason tracking."""
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        reason = request.POST.get('reason', '').strip()
        action_type = request.POST.get('action', 'cancel')

        new_status = 'closed' if action_type == 'close' else 'canceled'
        sub.status = new_status
        sub.closed_at = timezone.now()
        sub.cancellation_reason = reason
        sub.save(update_fields=['status', 'closed_at', 'cancellation_reason'])

        ActivityLog.objects.create(
            action=f"Subscription {sub.subscription_id} {new_status}",
            category="subscription",
            user=request.user,
            details=f"Reason: {reason}"
        )
        notify_subscription_status(sub, new_status.title(), reason)
        messages.info(request, f"Subscription {sub.subscription_id} has been {new_status}.")
        return redirect('subscription_detail', pk=sub.pk)


class SubscriptionRenewView(AdminRequiredMixin, View):
    """Manually renews a subscription and generates its renewal invoice."""
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        today = timezone.now().date()

        # Advance next billing date
        freq = sub.plan.billing_frequency.lower() if sub.plan else 'monthly'
        if freq == 'daily':
            next_date = today + timezone.timedelta(days=1)
        elif freq == 'weekly':
            next_date = today + timezone.timedelta(days=7)
        elif freq == 'yearly':
            next_date = today + timezone.timedelta(days=365)
        else:
            next_date = today + timezone.timedelta(days=30)

        sub.next_billing_date = next_date
        sub.status = 'active'
        sub.save(update_fields=['next_billing_date', 'status'])

        # Generate renewal invoice
        prefix = "INV"
        try:
            setting = SystemSetting.get_settings()
            if setting.invoice_prefix:
                prefix = setting.invoice_prefix.rstrip('-')
        except Exception:
            pass

        inv_num = f"{prefix}-{today.strftime('%Y%m')}-{random.randint(1000, 9999)}"
        invoice = Invoice.objects.create(
            invoice_number=inv_num,
            customer=sub.customer,
            subscription=sub,
            amount=sub.current_amount,
            tax_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=sub.current_amount,
            status='pending',
            issued_date=today,
            due_date=today + timezone.timedelta(days=15),
            notes=f"Manual renewal billing for {sub.plan.name}."
        )

        ActivityLog.objects.create(
            action=f"Renewed subscription {sub.subscription_id} (Generated Invoice {inv_num})",
            category="subscription",
            user=request.user
        )
        notify_subscription_status(sub, "Renewed")
        notify_invoice_generated(invoice)

        messages.success(request, f"Subscription {sub.subscription_id} renewed. Renewal invoice {inv_num} generated.")
        return redirect('subscription_detail', pk=sub.pk)


class SubscriptionDeleteView(AdminRequiredMixin, View):
    """Deletes draft or closed subscription."""
    def post(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        sub_id = sub.subscription_id
        sub.delete()
        ActivityLog.objects.create(
            action=f"Deleted subscription {sub_id}",
            category="subscription",
            user=request.user
        )
        messages.success(request, f"Subscription {sub_id} removed.")
        return redirect('subscription_list')


# ==============================================================================
# 3. QUOTATION MANAGEMENT VIEWS (PERSON 3 - SECTION 7)
# ==============================================================================

class QuotationListView(AdminRequiredMixin, View):
    """List and manage commercial quotations."""
    template_name = 'subscriptions/quotation_list.html'

    def get(self, request):
        queryset = Quotation.objects.select_related('customer', 'plan', 'variant').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(quotation_number__icontains=q) |
                Q(customer__full_name__icontains=q) |
                Q(customer__company_name__icontains=q)
            )
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        page_obj = paginate_queryset(request, queryset, per_page=12)
        context = {
            'page_obj': page_obj,
            'quotations': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'statuses': Quotation.STATUS_CHOICES,
            'page_title': 'Quotations Management',
        }
        return render(request, self.template_name, context)


class QuotationCreateView(AdminRequiredMixin, View):
    """Generate commercial quotation for client proposal."""
    template_name = 'subscriptions/quotation_form.html'

    def get(self, request):
        initial = {}
        cust_id = request.GET.get('customer')
        if cust_id:
            cust = Customer.objects.filter(pk=cust_id).first()
            if cust:
                initial['customer'] = cust
        form = QuotationForm(initial=initial)
        return render(request, self.template_name, {'form': form, 'page_title': 'Create Quotation', 'action': 'Create'})

    def post(self, request):
        form = QuotationForm(request.POST)
        if form.is_valid():
            qt = form.save()
            ActivityLog.objects.create(
                action=f"Created quotation {qt.quotation_number} for {qt.customer.full_name}",
                category="quotation",
                user=request.user,
                details=f"Amount: ${qt.total_amount}, Plan: {qt.plan.name}"
            )
            messages.success(request, f"Quotation {qt.quotation_number} generated successfully.")
            return redirect('quotation_detail', pk=qt.pk)
        return render(request, self.template_name, {'form': form, 'page_title': 'Create Quotation', 'action': 'Create'})


class QuotationDetailView(AdminRequiredMixin, View):
    """Official printable proposal view for commercial quotation."""
    template_name = 'subscriptions/quotation_detail.html'

    def get(self, request, pk):
        quotation = get_object_or_404(Quotation.objects.select_related('customer', 'plan', 'variant', 'tax_rate', 'discount', 'converted_subscription'), pk=pk)
        context = {
            'quotation': quotation,
            'page_title': f"Quotation {quotation.quotation_number}",
        }
        return render(request, self.template_name, context)


class QuotationUpdateView(AdminRequiredMixin, View):
    """Update quotation parameters."""
    template_name = 'subscriptions/quotation_form.html'

    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        form = QuotationForm(instance=quotation)
        return render(request, self.template_name, {'form': form, 'quotation': quotation, 'page_title': f'Edit Quotation: {quotation.quotation_number}', 'action': 'Update'})

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        form = QuotationForm(request.POST, instance=quotation)
        if form.is_valid():
            quotation = form.save()
            ActivityLog.objects.create(
                action=f"Updated quotation {quotation.quotation_number}",
                category="quotation",
                user=request.user
            )
            messages.success(request, f"Quotation {quotation.quotation_number} updated.")
            return redirect('quotation_detail', pk=quotation.pk)
        return render(request, self.template_name, {'form': form, 'quotation': quotation, 'page_title': f'Edit Quotation: {quotation.quotation_number}', 'action': 'Update'})


class QuotationConvertToSubscriptionView(AdminRequiredMixin, View):
    """1-Click Conversion: Converts approved quotation directly into an active subscription and creates invoice (Section 7)."""
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        if quotation.converted_subscription:
            messages.info(request, f"This quotation has already been converted to Subscription {quotation.converted_subscription.subscription_id}.")
            return redirect('subscription_detail', pk=quotation.converted_subscription.pk)

        today = timezone.now().date()
        rand_code = random.randint(1000, 9999)
        sub_id = f"SUB-{today.strftime('%Y%m')}-{rand_code}"
        while Subscription.objects.filter(subscription_id=sub_id).exists():
            rand_code = random.randint(1000, 9999)
            sub_id = f"SUB-{today.strftime('%Y%m')}-{rand_code}"

        # Determine billing renewal date
        freq = quotation.plan.billing_frequency.lower() if quotation.plan else 'monthly'
        if freq == 'daily':
            next_bill = today + timezone.timedelta(days=1)
        elif freq == 'weekly':
            next_bill = today + timezone.timedelta(days=7)
        elif freq == 'yearly':
            next_bill = today + timezone.timedelta(days=365)
        else:
            next_bill = today + timezone.timedelta(days=30)

        subscription = Subscription.objects.create(
            subscription_id=sub_id,
            customer=quotation.customer,
            plan=quotation.plan,
            variant=quotation.variant,
            quantity=quotation.quantity or 1,
            status='active',
            billing_cycle=quotation.plan.billing_frequency,
            current_amount=quotation.total_amount,
            payment_terms="Net 15",
            start_date=today,
            next_billing_date=next_bill,
            auto_renew=True
        )

        # Generate initial invoice
        inv_num = f"INV-{today.strftime('%Y%m')}-{random.randint(1000, 9999)}"
        invoice = Invoice.objects.create(
            invoice_number=inv_num,
            customer=quotation.customer,
            subscription=subscription,
            amount=quotation.subtotal or quotation.total_amount,
            tax_rate=quotation.tax_rate,
            tax_amount=quotation.tax_amount,
            discount=quotation.discount,
            discount_amount=quotation.discount_amount,
            total_amount=quotation.total_amount,
            status='pending',
            issued_date=today,
            due_date=today + timezone.timedelta(days=15),
            notes=f"Initial invoice generated from approved Quotation {quotation.quotation_number}."
        )

        # Mark quotation converted
        quotation.converted_subscription = subscription
        quotation.status = 'converted'
        quotation.save(update_fields=['converted_subscription', 'status'])

        ActivityLog.objects.create(
            action=f"Converted quotation {quotation.quotation_number} to Subscription {subscription.subscription_id}",
            category="subscription",
            user=request.user
        )
        notify_subscription_status(subscription, "Converted from Quotation & Activated")
        notify_invoice_generated(invoice)

        messages.success(request, f"Quotation successfully converted! Subscription {subscription.subscription_id} activated and Invoice {inv_num} issued.")
        return redirect('subscription_detail', pk=subscription.pk)


class QuotationDeleteView(AdminRequiredMixin, View):
    """Deletes draft quotation."""
    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        num = quotation.quotation_number
        quotation.delete()
        ActivityLog.objects.create(
            action=f"Deleted quotation {num}",
            category="quotation",
            user=request.user
        )
        messages.success(request, f"Quotation {num} deleted.")
        return redirect('quotation_list')


# ==============================================================================
# 2. INVOICE MANAGEMENT VIEWS (PERSON 4)
# ==============================================================================

class InvoiceListView(AdminRequiredMixin, View):
    """List invoices with status highlights, KPI summary, and direct actions."""
    template_name = 'subscriptions/invoice_list.html'

    def get(self, request):
        queryset = Invoice.objects.select_related('customer', 'subscription', 'tax_rate').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(invoice_number__icontains=q) |
                Q(customer__full_name__icontains=q) |
                Q(customer__email__icontains=q)
            )
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Financial KPI calculations
        total_invoiced = Invoice.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        paid_invoices_sum = Invoice.objects.filter(status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        overdue_invoices_sum = Invoice.objects.filter(status='overdue').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        pending_invoices_sum = Invoice.objects.filter(status='pending').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'invoices': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'total_invoiced': total_invoiced,
            'paid_invoices_sum': paid_invoices_sum,
            'overdue_invoices_sum': overdue_invoices_sum,
            'pending_invoices_sum': pending_invoices_sum,
            'page_title': 'Invoices & Billing Management',
        }
        return render(request, self.template_name, context)


class InvoiceCreateView(AdminRequiredMixin, View):
    """Create a new invoice with automated number and tax calculation."""
    template_name = 'subscriptions/invoice_form.html'

    def get(self, request):
        form = InvoiceForm()
        customer_id = request.GET.get('customer_id')
        if customer_id:
            form.fields['customer'].initial = customer_id
        subscription_id = request.GET.get('subscription_id')
        if subscription_id:
            form.fields['subscription'].initial = subscription_id
            try:
                sub = Subscription.objects.get(pk=subscription_id)
                form.fields['amount'].initial = sub.current_amount
            except Subscription.DoesNotExist:
                pass

        context = {
            'form': form,
            'page_title': 'Generate New Customer Invoice',
            'is_edit': False,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save()
            ActivityLog.objects.create(
                action=f"Created Invoice #{invoice.invoice_number}",
                category="invoice",
                user=request.user,
                details=f"Customer: {invoice.customer.full_name}, Total: {invoice.total_amount}"
            )
            messages.success(request, f"Invoice {invoice.invoice_number} created successfully.")
            return redirect('invoice_detail', pk=invoice.pk)
        
        messages.error(request, "Please correct the form errors indicated below.")
        context = {
            'form': form,
            'page_title': 'Generate New Customer Invoice',
            'is_edit': False,
        }
        return render(request, self.template_name, context)


class InvoiceDetailView(AdminRequiredMixin, View):
    """Printable invoice view with line items, tax details, and payment history."""
    template_name = 'subscriptions/invoice_detail.html'

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.select_related('customer', 'subscription', 'tax_rate', 'discount'),
            pk=pk
        )
        payments = invoice.payments.all().order_by('-payment_date')
        setting = SystemSetting.get_settings()
        
        context = {
            'invoice': invoice,
            'payments': payments,
            'setting': setting,
            'page_title': f"Invoice #{invoice.invoice_number}",
        }
        return render(request, self.template_name, context)


class InvoiceUpdateView(AdminRequiredMixin, View):
    """Edit invoice parameters, due dates, notes, and statuses."""
    template_name = 'subscriptions/invoice_form.html'

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceForm(instance=invoice)
        context = {
            'form': form,
            'invoice': invoice,
            'page_title': f"Edit Invoice #{invoice.invoice_number}",
            'is_edit': True,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            invoice = form.save()
            ActivityLog.objects.create(
                action=f"Updated Invoice #{invoice.invoice_number}",
                category="invoice",
                user=request.user,
                details=f"Status: {invoice.status}, Total: {invoice.total_amount}"
            )
            messages.success(request, f"Invoice {invoice.invoice_number} updated successfully.")
            return redirect('invoice_detail', pk=invoice.pk)

        messages.error(request, "Please correct the form errors indicated below.")
        context = {
            'form': form,
            'invoice': invoice,
            'page_title': f"Edit Invoice #{invoice.invoice_number}",
            'is_edit': True,
        }
        return render(request, self.template_name, context)


class InvoiceDeleteView(AdminRequiredMixin, View):
    """Delete an invoice with confirmation."""
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        num = invoice.invoice_number
        invoice.delete()
        ActivityLog.objects.create(
            action=f"Deleted Invoice #{num}",
            category="invoice",
            user=request.user
        )
        messages.success(request, f"Invoice {num} was deleted successfully.")
        return redirect('invoice_list')


class InvoiceMarkPaidView(AdminRequiredMixin, View):
    """1-click action to mark an invoice as paid and record completed payment."""
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        invoice.status = 'paid'
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=['status', 'paid_at'])

        # Auto-create completed payment record if balance exists
        if invoice.balance_due > Decimal('0.00'):
            Payment.objects.create(
                payment_id=f"PAY-{timezone.now().strftime('%Y%m')}-{random.randint(10000, 99999)}",
                customer=invoice.customer,
                invoice=invoice,
                amount=invoice.balance_due,
                payment_method='credit_card',
                status='completed',
                transaction_reference=f"admin_manual_{request.user.username}",
                payment_date=timezone.now(),
                notes="Marked as paid manually by administrator."
            )

        ActivityLog.objects.create(
            action=f"Marked Invoice #{invoice.invoice_number} as Paid",
            category="invoice",
            user=request.user
        )
        messages.success(request, f"Invoice {invoice.invoice_number} marked as Paid.")
        return redirect('invoice_detail', pk=invoice.pk)


# ==============================================================================
# 3. DISCOUNT MANAGEMENT VIEWS (PERSON 4)
# ==============================================================================

class DiscountListView(AdminRequiredMixin, View):
    """List promotional discounts, coupons, and active redemptions."""
    template_name = 'subscriptions/discount_list.html'

    def get(self, request):
        queryset = Discount.objects.all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(code__icontains=q) |
                Q(description__icontains=q)
            )
        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'discounts': page_obj.object_list,
            'search_query': q,
            'active_count': Discount.objects.filter(is_active=True).count(),
            'total_redemptions': Discount.objects.aggregate(Sum('times_used'))['times_used__sum'] or 0,
            'page_title': 'Discounts & Promotions Management',
        }
        return render(request, self.template_name, context)


class DiscountCreateView(AdminRequiredMixin, View):
    """Create a new promotional discount or coupon code."""
    template_name = 'subscriptions/discount_form.html'

    def get(self, request):
        form = DiscountForm()
        return render(request, self.template_name, {'form': form, 'page_title': 'Create Promotional Coupon', 'is_edit': False})

    def post(self, request):
        form = DiscountForm(request.POST)
        if form.is_valid():
            disc = form.save()
            ActivityLog.objects.create(
                action=f"Created Promo Code '{disc.code}'",
                category="discount",
                user=request.user,
                details=f"Type: {disc.discount_type}, Value: {disc.value}"
            )
            messages.success(request, f"Discount coupon '{disc.code}' created successfully.")
            return redirect('discount_list')
        messages.error(request, "Please correct the form errors indicated below.")
        return render(request, self.template_name, {'form': form, 'page_title': 'Create Promotional Coupon', 'is_edit': False})


class DiscountUpdateView(AdminRequiredMixin, View):
    """Edit promotional discount or coupon code."""
    template_name = 'subscriptions/discount_form.html'

    def get(self, request, pk):
        disc = get_object_or_404(Discount, pk=pk)
        form = DiscountForm(instance=disc)
        return render(request, self.template_name, {'form': form, 'discount': disc, 'page_title': f"Edit Discount '{disc.code}'", 'is_edit': True})

    def post(self, request, pk):
        disc = get_object_or_404(Discount, pk=pk)
        form = DiscountForm(request.POST, instance=disc)
        if form.is_valid():
            disc = form.save()
            ActivityLog.objects.create(
                action=f"Updated Promo Code '{disc.code}'",
                category="discount",
                user=request.user
            )
            messages.success(request, f"Discount coupon '{disc.code}' updated successfully.")
            return redirect('discount_list')
        messages.error(request, "Please correct the form errors indicated below.")
        return render(request, self.template_name, {'form': form, 'discount': disc, 'page_title': f"Edit Discount '{disc.code}'", 'is_edit': True})


class DiscountDeleteView(AdminRequiredMixin, View):
    """Delete a promotional discount code."""
    def post(self, request, pk):
        disc = get_object_or_404(Discount, pk=pk)
        code = disc.code
        disc.delete()
        ActivityLog.objects.create(
            action=f"Deleted Promo Code '{code}'",
            category="discount",
            user=request.user
        )
        messages.success(request, f"Discount coupon '{code}' was deleted.")
        return redirect('discount_list')


class DiscountToggleStatusView(AdminRequiredMixin, View):
    """1-click toggle to activate or deactivate a promo code."""
    def post(self, request, pk):
        disc = get_object_or_404(Discount, pk=pk)
        disc.is_active = not disc.is_active
        disc.save(update_fields=['is_active'])
        label = "activated" if disc.is_active else "deactivated"
        messages.info(request, f"Discount '{disc.code}' has been {label}.")
        return redirect('discount_list')


# ==============================================================================
# 4. PAYMENT MANAGEMENT VIEWS (PERSON 4)
# ==============================================================================

class PaymentListView(AdminRequiredMixin, View):
    """List and audit payment transactions with KPI metrics."""
    template_name = 'subscriptions/payment_list.html'

    def get(self, request):
        queryset = Payment.objects.select_related('customer', 'invoice').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(payment_id__icontains=q) |
                Q(customer__full_name__icontains=q) |
                Q(transaction_reference__icontains=q)
            )
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        total_collected = Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        pending_payments = Payment.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'payments': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'total_collected': total_collected,
            'pending_payments': pending_payments,
            'page_title': 'Payments & Transaction Log',
        }
        return render(request, self.template_name, context)


class PaymentCreateView(AdminRequiredMixin, View):
    """Record customer payment with automatic invoice settlement."""
    template_name = 'subscriptions/payment_form.html'

    def get(self, request):
        form = PaymentForm()
        invoice_id = request.GET.get('invoice_id')
        if invoice_id:
            try:
                inv = Invoice.objects.get(pk=invoice_id)
                form.fields['invoice'].initial = inv
                form.fields['customer'].initial = inv.customer
                form.fields['amount'].initial = inv.balance_due
            except Invoice.DoesNotExist:
                pass

        context = {
            'form': form,
            'page_title': 'Record Customer Payment',
            'is_edit': False,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            ActivityLog.objects.create(
                action=f"Recorded Payment #{payment.payment_id}",
                category="payment",
                user=request.user,
                details=f"Amount: {payment.amount}, Customer: {payment.customer.full_name}"
            )
            messages.success(request, f"Payment {payment.payment_id} recorded successfully.")
            return redirect('payment_detail', pk=payment.pk)

        messages.error(request, "Please correct the form errors indicated below.")
        context = {
            'form': form,
            'page_title': 'Record Customer Payment',
            'is_edit': False,
        }
        return render(request, self.template_name, context)


class PaymentDetailView(AdminRequiredMixin, View):
    """Official printable payment receipt view."""
    template_name = 'subscriptions/payment_detail.html'

    def get(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.select_related('customer', 'invoice'),
            pk=pk
        )
        setting = SystemSetting.get_settings()
        context = {
            'payment': payment,
            'setting': setting,
            'page_title': f"Payment Receipt #{payment.payment_id}",
        }
        return render(request, self.template_name, context)


class PaymentRefundView(AdminRequiredMixin, View):
    """Process a refund for a payment and update the associated invoice."""
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        payment.status = 'refunded'
        payment.save(update_fields=['status'])

        if payment.invoice:
            payment.invoice.status = 'refunded'
            payment.invoice.save(update_fields=['status'])

        ActivityLog.objects.create(
            action=f"Refunded Payment #{payment.payment_id}",
            category="payment",
            user=request.user,
            details=f"Amount: {payment.amount}"
        )
        messages.warning(request, f"Payment {payment.payment_id} has been marked as Refunded.")
        return redirect('payment_detail', pk=payment.pk)


# ==============================================================================
# 5. TAX CONFIGURATION VIEWS (PERSON 4)
# ==============================================================================

class TaxConfigurationView(AdminRequiredMixin, View):
    """Manage tax jurisdictions, rates (GST, VAT, Sales Tax), and system defaults."""
    template_name = 'subscriptions/tax_configuration.html'

    def get(self, request):
        tax_rates = TaxRate.objects.all().order_by('-is_default', 'name')
        form = TaxRateForm()
        total_tax_collected = Invoice.objects.filter(status='paid').aggregate(Sum('tax_amount'))['tax_amount__sum'] or Decimal('0.00')
        setting = SystemSetting.get_settings()
        
        context = {
            'tax_rates': tax_rates,
            'form': form,
            'total_tax_collected': total_tax_collected,
            'system_default_rate': setting.tax_rate,
            'page_title': 'Tax Rates & Rules Configuration',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = TaxRateForm(request.POST)
        if form.is_valid():
            tr = form.save()
            ActivityLog.objects.create(
                action=f"Created Tax Rate '{tr.name}' ({tr.rate_percent}%)",
                category="setting",
                user=request.user
            )
            messages.success(request, f"Tax Rate '{tr.name}' ({tr.rate_percent}%) created successfully.")
            return redirect('tax_configuration')

        tax_rates = TaxRate.objects.all().order_by('-is_default', 'name')
        total_tax_collected = Invoice.objects.filter(status='paid').aggregate(Sum('tax_amount'))['tax_amount__sum'] or Decimal('0.00')
        setting = SystemSetting.get_settings()
        context = {
            'tax_rates': tax_rates,
            'form': form,
            'total_tax_collected': total_tax_collected,
            'system_default_rate': setting.tax_rate,
            'page_title': 'Tax Rates & Rules Configuration',
        }
        return render(request, self.template_name, context)


class TaxRateSetDefaultView(AdminRequiredMixin, View):
    """Set a tax rate as the default across the application."""
    def post(self, request, pk):
        tax_rate = get_object_or_404(TaxRate, pk=pk)
        TaxRate.objects.filter(is_default=True).update(is_default=False)
        tax_rate.is_default = True
        tax_rate.save(update_fields=['is_default'])

        # Keep SystemSetting in sync
        setting = SystemSetting.get_settings()
        setting.tax_rate = tax_rate.rate_percent
        setting.save(update_fields=['tax_rate'])

        ActivityLog.objects.create(
            action=f"Set Default Tax Rate to '{tax_rate.name}' ({tax_rate.rate_percent}%)",
            category="setting",
            user=request.user
        )
        messages.success(request, f"'{tax_rate.name}' ({tax_rate.rate_percent}%) is now the default tax rate.")
        return redirect('tax_configuration')


class TaxRateDeleteView(AdminRequiredMixin, View):
    """Delete a tax rate configuration."""
    def post(self, request, pk):
        tax_rate = get_object_or_404(TaxRate, pk=pk)
        name = tax_rate.name
        tax_rate.delete()
        ActivityLog.objects.create(
            action=f"Deleted Tax Rate '{name}'",
            category="setting",
            user=request.user
        )
        messages.success(request, f"Tax Rate '{name}' deleted.")
        return redirect('tax_configuration')


# ==============================================================================
# 6. REAL-TIME CALCULATION API HELPER
# ==============================================================================

class InvoiceCalculatePreviewView(AdminRequiredMixin, View):
    """JSON API to preview discount, tax, and total before saving an invoice."""
    def get(self, request):
        from decimal import Decimal, InvalidOperation
        try:
            subtotal = Decimal(request.GET.get('amount', '0.00'))
        except (InvalidOperation, ValueError):
            subtotal = Decimal('0.00')

        discount_id = request.GET.get('discount_id')
        discount_amount = Decimal('0.00')
        if discount_id:
            try:
                disc = Discount.objects.get(pk=discount_id)
                discount_amount = disc.calculate_discount(subtotal)
            except (Discount.DoesNotExist, ValueError):
                pass

        taxable = max(Decimal('0.00'), subtotal - discount_amount)
        tax_rate_id = request.GET.get('tax_rate_id')
        tax_percent = Decimal('18.00')
        if tax_rate_id:
            try:
                tr = TaxRate.objects.get(pk=tax_rate_id)
                tax_percent = tr.rate_percent
            except (TaxRate.DoesNotExist, ValueError):
                pass
        else:
            try:
                setting = SystemSetting.get_settings()
                tax_percent = setting.tax_rate or Decimal('18.00')
            except Exception:
                pass

        tax_amount = round(taxable * (tax_percent / Decimal('100.00')), 2)
        total_amount = round(taxable + tax_amount, 2)

        return JsonResponse({
            'subtotal': float(subtotal),
            'discount_amount': float(discount_amount),
            'taxable_amount': float(taxable),
            'tax_percent': float(tax_percent),
            'tax_amount': float(tax_amount),
            'total_amount': float(total_amount),
        })
