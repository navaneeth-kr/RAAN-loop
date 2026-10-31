from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from products.models import Product, ProductVariant

class SubscriptionPlan(models.Model):
    """
    Subscription Plan Management Module.
    Connects with Products and Variants, manages billing frequencies (Daily, Weekly, Monthly, Yearly),
    date availability, quantity pricing rules, policy configurations, and safe deletion controls.
    """
    TIER_CHOICES = [
        ('starter', 'Starter'),
        ('growth', 'Growth / Pro'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom / Enterprise Plus'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Yearly'),  # Backward compatibility
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]

    # Core Plan Fields
    name = models.CharField(max_length=150, verbose_name="Plan Name")
    code = models.CharField(max_length=50, unique=True, verbose_name="Plan Code / SKU")
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='plans', verbose_name="Associated Product")
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plans',
        verbose_name="Product Variant",
        help_text="Optional linked variant configuration"
    )
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='growth')
    
    # Billing Frequency (Daily, Weekly, Monthly, Yearly)
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly',
        verbose_name="Billing Frequency"
    )

    # Pricing & Quantities
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Unit Price",
        help_text="Base recurring price per unit/seat"
    )
    min_quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Minimum Quantity",
        help_text="Minimum seats/units required to purchase this plan"
    )
    trial_days = models.PositiveIntegerField(default=14, verbose_name="Trial Days", help_text="Free trial duration in days")
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Setup Fee")

    # Dates & Availability
    start_date = models.DateField(default=timezone.now, verbose_name="Start Date", help_text="Date when plan becomes available")
    end_date = models.DateField(null=True, blank=True, verbose_name="End Date", help_text="Optional date when plan expires or retires")

    # Policy Configurations
    auto_close = models.BooleanField(
        default=False,
        verbose_name="Automatic Closure",
        help_text="Automatically close/retire plan when end date is reached"
    )
    allow_early_cancellation = models.BooleanField(
        default=True,
        verbose_name="Allow Early Cancellation",
        help_text="Allow subscribers to cancel before billing term ends"
    )
    allow_pausing = models.BooleanField(
        default=True,
        verbose_name="Allow Pausing",
        help_text="Allow subscribers to temporarily pause active subscription"
    )
    allow_renewal = models.BooleanField(
        default=True,
        verbose_name="Allow Renewal",
        help_text="Allow automatic or manual subscription renewal"
    )

    # Status & Meta
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Plan Status")
    is_featured = models.BooleanField(default=False, help_text="Display as 'Most Popular' plan")
    sort_order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, help_text="Plan summary and marketing highlights")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price']
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"

    def save(self, *args, **kwargs):
        if not self.slug:
            product_name = self.product.name if self.product else "product"
            base_slug = slugify(f"{product_name}-{self.name}")
            slug = base_slug
            counter = 1
            while SubscriptionPlan.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.product.name} (₹{self.price}/{self.get_billing_cycle_display()})"

    @property
    def billing_frequency(self):
        """Alias for billing_cycle display."""
        return self.get_billing_cycle_display()

    @billing_frequency.setter
    def billing_frequency(self, value):
        self.billing_cycle = value

    def calculate_price_for_quantity(self, quantity=1):
        """
        Calculate total price based on unit price and quantity.
        Enforces minimum quantity constraint.
        Formula: Total Price = Unit Price * max(quantity, min_quantity)
        """
        qty = max(int(quantity or 1), self.min_quantity)
        return round(self.price * qty, 2)

    @property
    def monthly_equivalent(self):
        """Calculates normalized monthly equivalent for comparison."""
        if self.billing_cycle in ['yearly', 'annual']:
            return round(self.price / 12, 2)
        elif self.billing_cycle == 'quarterly':
            return round(self.price / 3, 2)
        elif self.billing_cycle == 'weekly':
            return round(self.price * Decimal('4.33'), 2)
        elif self.billing_cycle == 'daily':
            return round(self.price * 30, 2)
        return self.price

    @property
    def active_subscriptions_count(self):
        """Active, trialing, or past_due subscriptions currently attached to this plan."""
        if hasattr(self, 'subscriptions'):
            return self.subscriptions.filter(status__in=['active', 'trialing', 'past_due']).count()
        return 0

    @property
    def total_subscriptions_count(self):
        """Total subscriptions attached to this plan across all states."""
        return self.subscriptions.count() if hasattr(self, 'subscriptions') else 0

    def can_be_safely_deleted(self):
        """
        Safety Check: Prevent deletion of plans that are already used by active subscriptions.
        Returns: (can_delete: bool, reason: str)
        """
        active_count = self.active_subscriptions_count
        if active_count > 0:
            return False, f"Plan '{self.name}' has {active_count} active subscription(s). Plans in active use cannot be deleted. You can deactivate the plan instead."
        return True, ""

    @property
    def is_currently_active(self):
        """Checks if the plan is active and within valid start and end dates."""
        today = timezone.now().date()
        if self.status != 'active':
            return False
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True

    @property
    def badge_class(self):
        mapping = {
            'active': 'success',
            'inactive': 'warning',
            'archived': 'secondary',
        }
        return mapping.get(self.status, 'primary')


class PlanFeature(models.Model):
    """Specific feature or limit included in a subscription plan."""
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=150, help_text="e.g. Max Projects, Automated Backups, Dedicated Support")
    quota_value = models.CharField(max_length=100, default="Included", help_text="e.g. 'Unlimited', '25 Users', 'Yes'")
    is_included = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = "Plan Feature"
        verbose_name_plural = "Plan Features"

    def __str__(self):
        return f"{self.name}: {self.quota_value} ({self.plan.name})"
