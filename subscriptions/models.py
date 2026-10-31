from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from products.models import Product, ProductVariant
from plans.models import SubscriptionPlan

class Customer(models.Model):
    """Customer profile linked to authentication and financial records."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_profile')
    full_name = models.CharField(max_length=150, verbose_name="Customer / Contact Name")
    company_name = models.CharField(max_length=150, blank=True, verbose_name="Organization / Company")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True, verbose_name="Billing Address")
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, blank=True, default="India")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, help_text="Internal account notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.company_name or self.email})"

    @property
    def active_subscriptions_count(self):
        return self.subscriptions.filter(status='active').count()

    @property
    def total_spent(self):
        from decimal import Decimal
        return self.payments.filter(status='completed').aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')

    @property
    def unpaid_balance(self):
        from decimal import Decimal
        invoices = self.invoices.filter(status__in=['pending', 'overdue'])
        total_due = invoices.aggregate(models.Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        return total_due


class Subscription(models.Model):
    """Customer subscription lifecycle management."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('quotation', 'Quotation Pending'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('trialing', 'Trialing'),
        ('past_due', 'Past Due'),
        ('paused', 'Paused'),
        ('canceled', 'Canceled'),
        ('closed', 'Closed'),
    ]

    subscription_id = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity / Seats")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    billing_cycle = models.CharField(max_length=20, default='monthly')
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Recurring period charge")
    payment_terms = models.CharField(max_length=50, default="Net 15", verbose_name="Payment Terms")
    start_date = models.DateField(default=timezone.now)
    next_billing_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True, help_text="Definitive subscription termination date if non-renewing")
    auto_renew = models.BooleanField(default=True)
    cancellation_reason = models.TextField(blank=True, help_text="Documented reason for pause or cancellation")
    paused_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subscription_id} - {self.customer.full_name} ({self.plan.name})"

    @property
    def status_badge_class(self):
        mapping = {
            'active': 'success',
            'trialing': 'info',
            'confirmed': 'primary',
            'draft': 'secondary',
            'quotation': 'info',
            'past_due': 'danger',
            'canceled': 'dark',
            'closed': 'secondary',
            'paused': 'warning',
        }
        return mapping.get(self.status, 'primary')

    @property
    def days_until_renewal(self):
        today = timezone.now().date()
        if self.next_billing_date:
            return (self.next_billing_date - today).days
        return 999

    @property
    def is_expiring_soon(self):
        return 0 <= self.days_until_renewal <= 7

    @property
    def can_pause(self):
        return self.status == 'active' and self.plan.allow_pausing

    @property
    def can_resume(self):
        return self.status == 'paused'

    @property
    def can_cancel(self):
        return self.status not in ['canceled', 'closed'] and self.plan.allow_early_cancellation

    @property
    def can_renew(self):
        return self.status in ['active', 'past_due', 'trialing', 'confirmed'] and self.plan.allow_renewal



class TaxRate(models.Model):
    """Tax configuration rules (e.g. GST 18%, VAT 20%, Sales Tax 8.25%)."""
    name = models.CharField(max_length=100, verbose_name="Tax Name")
    rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, verbose_name="Tax Rate (%)")
    description = models.CharField(max_length=255, blank=True)
    is_default = models.BooleanField(default=False, verbose_name="Default Tax Rate")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.rate_percent}%)"


class Invoice(models.Model):
    """Billing invoices with due date tracking."""
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('overdue', 'Overdue'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Subtotal before tax & discounts")
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.ForeignKey('Discount', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    issued_date = models.DateField(default=timezone.now)
    due_date = models.DateField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Public or internal invoice remarks")

    class Meta:
        ordering = ['-issued_date']

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.full_name} (${self.total_amount})"

    @property
    def is_overdue(self):
        return self.status == 'overdue' or (self.status == 'pending' and self.due_date < timezone.now().date())

    @property
    def status_badge_class(self):
        mapping = {
            'paid': 'success',
            'pending': 'warning',
            'overdue': 'danger',
            'failed': 'danger',
            'refunded': 'secondary',
        }
        return mapping.get(self.status, 'primary')

    @property
    def paid_amount(self):
        from decimal import Decimal
        return self.payments.filter(status='completed').aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')

    @property
    def balance_due(self):
        from decimal import Decimal
        return max(Decimal('0.00'), self.total_amount - self.paid_amount)


class Payment(models.Model):
    """Payments made for invoices or subscriptions."""
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI / NetBanking'),
    ]

    payment_id = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=METHOD_CHOICES, default='credit_card')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    transaction_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.payment_id} - ${self.amount} ({self.get_status_display()})"

    @property
    def status_badge_class(self):
        mapping = {
            'completed': 'success',
            'pending': 'warning',
            'failed': 'danger',
            'refunded': 'secondary',
        }
        return mapping.get(self.status, 'primary')



class Quotation(models.Model):
    """Custom quotations for enterprise or bespoke subscriptions."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent / Pending Review'),
        ('accepted', 'Accepted'),
        ('converted', 'Converted to Subscription'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
    ]

    quotation_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='quotations')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='quotations')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity / Seats")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_rate = models.ForeignKey('TaxRate', on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.ForeignKey('Discount', on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    validity_days = models.PositiveIntegerField(default=30, help_text="Quotation validity period in days")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    notes = models.TextField(blank=True, help_text="Special terms, inclusions, or customer notes")
    valid_until = models.DateField()
    converted_subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_quotations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quotation_number} - {self.customer.full_name} (${self.total_amount})"

    @property
    def is_expired(self):
        return self.valid_until < timezone.now().date() and self.status not in ['accepted', 'converted']

    @property
    def can_convert(self):
        return self.status in ['sent', 'accepted'] and not self.converted_subscription

    @property
    def status_badge_class(self):
        mapping = {
            'draft': 'secondary',
            'sent': 'info',
            'accepted': 'primary',
            'converted': 'success',
            'expired': 'warning',
            'rejected': 'danger',
        }
        return mapping.get(self.status, 'primary')


class Discount(models.Model):
    """Discounts and promo codes."""
    TYPE_CHOICES = [
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount ($)'),
    ]

    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='percentage')
    value = models.DecimalField(max_digits=8, decimal_places=2, help_text="Percentage off or dollar amount")
    valid_from = models.DateField(default=timezone.now)
    valid_until = models.DateField()
    is_active = models.BooleanField(default=True)
    times_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.value}{'%' if self.discount_type == 'percentage' else '$'})"

    def calculate_discount(self, subtotal):
        """Calculates discount amount applied to a given subtotal."""
        from decimal import Decimal
        sub = Decimal(str(subtotal or '0.00'))
        if self.discount_type == 'percentage':
            return round((sub * (self.value / Decimal('100.00'))), 2)
        else:
            return min(sub, self.value)

    @property
    def is_currently_valid(self):
        today = timezone.now().date()
        return self.is_active and (self.valid_from <= today <= self.valid_until)

    @property
    def status_badge_class(self):
        return 'success' if self.is_currently_valid else 'secondary'


class Notification(models.Model):
    """In-app notifications for users, staff, and customers."""
    CATEGORY_CHOICES = [
        ('renewal', 'Renewal Alert'),
        ('billing', 'Billing & Invoice'),
        ('payment', 'Payment Event'),
        ('subscription', 'Subscription Status'),
        ('security', 'Security & Account'),
        ('system', 'System Notification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='in_app_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='system')
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title} ({'Read' if self.is_read else 'Unread'})"

    @property
    def icon_class(self):
        mapping = {
            'renewal': 'bi-clock-history text-warning',
            'billing': 'bi-receipt text-info',
            'payment': 'bi-credit-card-check text-success',
            'subscription': 'bi-arrow-repeat text-primary',
            'security': 'bi-shield-check text-danger',
            'system': 'bi-bell-fill text-secondary',
        }
        return mapping.get(self.category, 'bi-bell text-secondary')

