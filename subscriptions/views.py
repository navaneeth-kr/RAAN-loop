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
from .forms import InvoiceForm, DiscountForm, PaymentForm, TaxRateForm

# ==============================================================================
# 1. CUSTOMER & SUBSCRIPTION VIEWS
# ==============================================================================

class CustomerListView(AdminRequiredMixin, View):
    """List and search customers."""
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

        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'customers': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'page_title': 'Customers Management',
        }
        return render(request, self.template_name, context)


class SubscriptionListView(AdminRequiredMixin, View):
    """List customer subscriptions with search and filtering."""
    template_name = 'subscriptions/subscription_list.html'

    def get(self, request):
        queryset = Subscription.objects.select_related('customer', 'plan').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(subscription_id__icontains=q) |
                Q(customer__full_name__icontains=q) |
                Q(customer__email__icontains=q) |
                Q(plan__name__icontains=q)
            )
        status = request.GET.get('status')
        if status in ['active', 'trialing', 'past_due', 'canceled']:
            queryset = queryset.filter(status=status)

        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'subscriptions': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'page_title': 'Subscription Lifecycle Management',
        }
        return render(request, self.template_name, context)


class QuotationListView(AdminRequiredMixin, View):
    """List and manage quotations."""
    template_name = 'subscriptions/quotation_list.html'

    def get(self, request):
        queryset = Quotation.objects.select_related('customer', 'plan').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(quotation_number__icontains=q) |
                Q(customer__full_name__icontains=q)
            )
        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'quotations': page_obj.object_list,
            'search_query': q,
            'page_title': 'Quotations Management',
        }
        return render(request, self.template_name, context)


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
