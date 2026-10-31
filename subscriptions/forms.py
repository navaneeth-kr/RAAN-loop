import random
from decimal import Decimal
from django import forms
from django.utils import timezone
from .models import Invoice, Payment, Discount, TaxRate, Customer, Subscription
from core.models import SystemSetting

class InvoiceForm(forms.ModelForm):
    """Admin form for creating and updating invoices with dynamic tax & discount calculations."""
    class Meta:
        model = Invoice
        fields = [
            'customer',
            'subscription',
            'amount',
            'tax_rate',
            'discount',
            'issued_date',
            'due_date',
            'status',
            'notes',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select', 'id': 'id_invoice_customer'}),
            'subscription': forms.Select(attrs={'class': 'form-select', 'id': 'id_invoice_subscription'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'id': 'id_invoice_amount', 'placeholder': '0.00'}),
            'tax_rate': forms.Select(attrs={'class': 'form-select', 'id': 'id_invoice_tax_rate'}),
            'discount': forms.Select(attrs={'class': 'form-select', 'id': 'id_invoice_discount'}),
            'issued_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add notes, payment instructions, or terms...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default dates
        if not self.instance.pk:
            self.fields['issued_date'].initial = timezone.now().date()
            self.fields['due_date'].initial = timezone.now().date() + timezone.timedelta(days=15)
            # Default tax rate
            default_tr = TaxRate.objects.filter(is_default=True, is_active=True).first()
            if default_tr:
                self.fields['tax_rate'].initial = default_tr
        
        # Only active tax rates and discounts
        self.fields['tax_rate'].queryset = TaxRate.objects.filter(is_active=True)
        self.fields['discount'].queryset = Discount.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        issued_date = cleaned_data.get('issued_date')
        due_date = cleaned_data.get('due_date')
        customer = cleaned_data.get('customer')
        subscription = cleaned_data.get('subscription')

        if amount is not None and amount <= Decimal('0.00'):
            self.add_error('amount', 'Invoice subtotal must be greater than zero.')

        if issued_date and due_date and due_date < issued_date:
            self.add_error('due_date', 'Due date cannot precede the invoice issue date.')

        if subscription and customer and subscription.customer != customer:
            self.add_error('subscription', f'The selected subscription does not belong to {customer.full_name}.')

        return cleaned_data

    def save(self, commit=True):
        invoice = super().save(commit=False)
        
        # Auto-generate unique invoice number if not already present
        if not invoice.invoice_number:
            prefix = "INV"
            try:
                setting = SystemSetting.get_settings()
                if setting.invoice_prefix:
                    prefix = setting.invoice_prefix.rstrip('-')
            except Exception:
                pass
            date_str = timezone.now().strftime('%Y%m')
            rand_code = random.randint(1000, 9999)
            invoice.invoice_number = f"{prefix}-{date_str}-{rand_code}"
            while Invoice.objects.filter(invoice_number=invoice.invoice_number).exists():
                rand_code = random.randint(1000, 9999)
                invoice.invoice_number = f"{prefix}-{date_str}-{rand_code}"

        # 1. Calculate discount
        subtotal = invoice.amount or Decimal('0.00')
        discount_amt = Decimal('0.00')
        if invoice.discount:
            discount_amt = invoice.discount.calculate_discount(subtotal)
        invoice.discount_amount = discount_amt

        taxable_base = max(Decimal('0.00'), subtotal - discount_amt)

        # 2. Calculate tax
        tax_pct = Decimal('0.00')
        if invoice.tax_rate:
            tax_pct = invoice.tax_rate.rate_percent
        else:
            try:
                setting = SystemSetting.get_settings()
                tax_pct = setting.tax_rate or Decimal('18.00')
            except Exception:
                tax_pct = Decimal('18.00')

        tax_amt = round(taxable_base * (tax_pct / Decimal('100.00')), 2)
        invoice.tax_amount = tax_amt

        # 3. Calculate total
        invoice.total_amount = round(taxable_base + tax_amt, 2)

        if invoice.status == 'paid' and not invoice.paid_at:
            invoice.paid_at = timezone.now()

        if commit:
            invoice.save()
            if invoice.discount:
                invoice.discount.times_used += 1
                invoice.discount.save(update_fields=['times_used'])

        return invoice


class DiscountForm(forms.ModelForm):
    """Admin form for promotional discount codes and coupons."""
    class Meta:
        model = Discount
        fields = [
            'code',
            'description',
            'discount_type',
            'value',
            'valid_from',
            'valid_until',
            'is_active',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control text-uppercase font-monospace fw-bold', 'placeholder': 'e.g. SUMMER25'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 25% Off Annual Plans'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['valid_from'].initial = timezone.now().date()
            self.fields['valid_until'].initial = timezone.now().date() + timezone.timedelta(days=60)
            self.fields['is_active'].initial = True

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError("Discount code cannot be blank.")
        qs = Discount.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Discount code '{code}' already exists. Please choose a unique code.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        dtype = cleaned_data.get('discount_type')
        val = cleaned_data.get('value')
        vfrom = cleaned_data.get('valid_from')
        vuntil = cleaned_data.get('valid_until')

        if val is not None and val <= Decimal('0.00'):
            self.add_error('value', 'Discount value must be greater than zero.')

        if dtype == 'percentage' and val is not None and val > Decimal('100.00'):
            self.add_error('value', 'Percentage discount cannot exceed 100%.')

        if vfrom and vuntil and vuntil < vfrom:
            self.add_error('valid_until', 'Expiration date cannot be earlier than start date.')

        return cleaned_data


class PaymentForm(forms.ModelForm):
    """Admin form for recording and updating customer payments."""
    class Meta:
        model = Payment
        fields = [
            'customer',
            'invoice',
            'amount',
            'payment_method',
            'transaction_reference',
            'payment_date',
            'status',
            'notes',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_customer'}),
            'invoice': forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_invoice'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'id': 'id_payment_amount', 'placeholder': '0.00'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'transaction_reference': forms.TextInput(attrs={'class': 'form-control font-monospace', 'placeholder': 'e.g. txn_stripe_987123 or wire_ref_001'}),
            'payment_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional internal notes...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['payment_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
            self.fields['status'].initial = 'completed'

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        customer = cleaned_data.get('customer')
        invoice = cleaned_data.get('invoice')

        if amount is not None and amount <= Decimal('0.00'):
            self.add_error('amount', 'Payment amount must be greater than zero.')

        if invoice and customer and invoice.customer != customer:
            self.add_error('invoice', f'Invoice {invoice.invoice_number} does not belong to {customer.full_name}.')

        return cleaned_data

    def save(self, commit=True):
        payment = super().save(commit=False)
        
        # Auto-generate payment ID if not set
        if not payment.payment_id:
            rand_code = random.randint(10000, 99999)
            payment.payment_id = f"PAY-{timezone.now().strftime('%Y%m')}-{rand_code}"
            while Payment.objects.filter(payment_id=payment.payment_id).exists():
                rand_code = random.randint(10000, 99999)
                payment.payment_id = f"PAY-{timezone.now().strftime('%Y%m')}-{rand_code}"

        if not payment.transaction_reference:
            payment.transaction_reference = f"tx_{random.randint(10000000, 99999999)}"

        if commit:
            payment.save()
            # If payment is completed and linked to invoice, auto-update invoice status
            if payment.invoice and payment.status == 'completed':
                inv = payment.invoice
                if inv.balance_due <= Decimal('0.00'):
                    inv.status = 'paid'
                    inv.paid_at = payment.payment_date or timezone.now()
                    inv.save(update_fields=['status', 'paid_at'])

        return payment


class TaxRateForm(forms.ModelForm):
    """Admin form for configuring regional and national tax rates."""
    class Meta:
        model = TaxRate
        fields = ['name', 'rate_percent', 'description', 'is_default', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard GST, State VAT, US Sales Tax'}),
            'rate_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00', 'max': '100.00', 'placeholder': '18.00'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief description or jurisdiction note'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_rate_percent(self):
        rate = self.cleaned_data.get('rate_percent')
        if rate is not None and (rate < Decimal('0.00') or rate > Decimal('100.00')):
            raise forms.ValidationError("Tax rate percentage must be between 0.00% and 100.00%.")
        return rate

    def save(self, commit=True):
        tax_rate = super().save(commit=False)
        # If this tax rate is set as default, remove default from others
        if tax_rate.is_default:
            TaxRate.objects.filter(is_default=True).exclude(pk=tax_rate.pk).update(is_default=False)
        if commit:
            tax_rate.save()
        return tax_rate
