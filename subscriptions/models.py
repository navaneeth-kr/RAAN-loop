from django.db import models
from django.utils import timezone
from products.models import Product, ProductVariant
from plans.models import SubscriptionPlan

class Customer(models.Model):
    """Customer profile (coordinated with Person 1)."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    full_name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, default="United States")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.company_name or self.email})"


class Subscription(models.Model):
    """Customer subscription lifecycle (coordinated with Person 3)."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('trialing', 'Trialing'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('paused', 'Paused'),
    ]

    subscription_id = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    billing_cycle = models.CharField(max_length=20, default='monthly')
    current_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(default=timezone.now)
    next_billing_date = models.DateField()
    auto_renew = models.BooleanField(default=True)
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
            'past_due': 'danger',
            'canceled': 'secondary',
            'paused': 'warning',
        }
        return mapping.get(self.status, 'primary')


class Invoice(models.Model):
    """Billing invoices (coordinated with Person 4)."""
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending Payment'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid')
    issued_date = models.DateField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-issued_date']

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.full_name} (${self.total_amount})"
