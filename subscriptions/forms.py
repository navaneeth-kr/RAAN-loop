import random
from decimal import Decimal
from django import forms
from django.utils import timezone
from .models import Invoice, Payment, Discount, TaxRate, Customer, Subscription, Quotation
from products.models import ProductVariant
from plans.models import SubscriptionPlan
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


class CustomerForm(forms.ModelForm):
    """Admin form for adding and modifying customer accounts."""
    class Meta:
        model = Customer
        fields = [
            'full_name',
            'company_name',
            'email',
            'phone',
            'address',
            'city',
            'postal_code',
            'country',
            'status',
            'notes',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Jane Doe'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Acme Corporation'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'jane@acme.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 019-2834'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address or Suite'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Internal account notes or SLA agreements...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['company_name', 'phone', 'address', 'city', 'postal_code', 'country', 'notes']:
            if field in self.fields:
                self.fields[field].required = False

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = Customer.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A customer account with this email address already exists.")
        return email


class SubscriptionForm(forms.ModelForm):
    """Admin form for creating and updating customer subscriptions."""
    class Meta:
        model = Subscription
        fields = [
            'customer',
            'plan',
            'variant',
            'quantity',
            'billing_cycle',
            'current_amount',
            'payment_terms',
            'start_date',
            'next_billing_date',
            'expiry_date',
            'auto_renew',
            'status',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select', 'id': 'id_sub_customer'}),
            'plan': forms.Select(attrs={'class': 'form-select', 'id': 'id_sub_plan'}),
            'variant': forms.Select(attrs={'class': 'form-select', 'id': 'id_sub_variant'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'id': 'id_sub_quantity'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select', 'id': 'id_sub_cycle'}, choices=[
                ('monthly', 'Monthly Billing'),
                ('yearly', 'Yearly Billing'),
                ('weekly', 'Weekly Billing'),
                ('daily', 'Daily Billing'),
            ]),
            'current_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00', 'placeholder': '0.00'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Net 15, Net 30, Due Upon Receipt'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_billing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'auto_renew': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now().date()
            self.fields['next_billing_date'].initial = timezone.now().date() + timezone.timedelta(days=30)
            self.fields['status'].initial = 'active'

    def save(self, commit=True):
        sub = super().save(commit=False)
        if not sub.subscription_id:
            rand_code = random.randint(1000, 9999)
            sub.subscription_id = f"SUB-{timezone.now().strftime('%Y%m')}-{rand_code}"
            while Subscription.objects.filter(subscription_id=sub.subscription_id).exists():
                rand_code = random.randint(1000, 9999)
                sub.subscription_id = f"SUB-{timezone.now().strftime('%Y%m')}-{rand_code}"

        # If current_amount is zero or not set, compute based on plan & quantity
        if not sub.current_amount and sub.plan:
            base_price = sub.plan.price
            if sub.variant:
                base_price += sub.variant.price_modifier
            sub.current_amount = base_price * sub.quantity

        if commit:
            sub.save()
        return sub


class SubscriptionActionForm(forms.Form):
    """Form for pausing, resuming, or canceling a subscription with reason tracking."""
    action = forms.ChoiceField(choices=[
        ('pause', 'Pause Subscription'),
        ('resume', 'Resume Active Status'),
        ('cancel', 'Cancel Subscription'),
        ('close', 'Close Subscription Early'),
    ], widget=forms.Select(attrs={'class': 'form-select'}))
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for lifecycle change (required for pause and cancel)...'})
    )


class QuotationForm(forms.ModelForm):
    """Form for generating commercial customer quotations."""
    class Meta:
        model = Quotation
        fields = [
            'customer',
            'plan',
            'variant',
            'quantity',
            'unit_price',
            'subtotal',
            'tax_rate',
            'discount',
            'total_amount',
            'validity_days',
            'notes',
            'status',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select', 'id': 'id_qt_customer'}),
            'plan': forms.Select(attrs={'class': 'form-select', 'id': 'id_qt_plan'}),
            'variant': forms.Select(attrs={'class': 'form-select', 'id': 'id_qt_variant'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'id': 'id_qt_quantity'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_qt_price', 'placeholder': '0.00'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_qt_subtotal', 'placeholder': '0.00'}),
            'tax_rate': forms.Select(attrs={'class': 'form-select', 'id': 'id_qt_tax'}),
            'discount': forms.Select(attrs={'class': 'form-select', 'id': 'id_qt_discount'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_qt_total', 'placeholder': '0.00'}),
            'validity_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 365}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Terms, custom deliverables, or scope details...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['validity_days'].initial = 30
            self.fields['status'].initial = 'sent'
            default_tr = TaxRate.objects.filter(is_default=True, is_active=True).first()
            if default_tr:
                self.fields['tax_rate'].initial = default_tr

    def save(self, commit=True):
        qt = super().save(commit=False)
        today = timezone.now().date()

        if not qt.quotation_number:
            rand_code = random.randint(1000, 9999)
            qt.quotation_number = f"QT-{today.strftime('%Y%m')}-{rand_code}"
            while Quotation.objects.filter(quotation_number=qt.quotation_number).exists():
                rand_code = random.randint(1000, 9999)
                qt.quotation_number = f"QT-{today.strftime('%Y%m')}-{rand_code}"

        # Calculate validity date
        val_days = qt.validity_days or 30
        qt.valid_until = today + timezone.timedelta(days=val_days)

        # Financial reconciliation
        sub = qt.subtotal or Decimal('0.00')
        if sub <= Decimal('0.00') and qt.plan:
            unit = qt.unit_price or qt.plan.price
            sub = unit * (qt.quantity or 1)
            qt.subtotal = sub

        disc_amt = Decimal('0.00')
        if qt.discount:
            disc_amt = qt.discount.calculate_discount(sub)
        qt.discount_amount = disc_amt

        tax_base = max(Decimal('0.00'), sub - disc_amt)
        tax_amt = Decimal('0.00')
        if qt.tax_rate:
            tax_amt = round(tax_base * (qt.tax_rate.rate_percent / Decimal('100.00')), 2)
        qt.tax_amount = tax_amt

        qt.total_amount = tax_base + tax_amt

        if commit:
            qt.save()
        return qt
