from django.db import models
from django.utils.text import slugify
from products.models import Product, ProductVariant

class SubscriptionPlan(models.Model):
    """Recurring Subscription Plan tied to Products & Variants."""
    TIER_CHOICES = [
        ('starter', 'Starter'),
        ('growth', 'Growth / Pro'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom / Enterprise Plus'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('biannual', 'Bi-Annual'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, verbose_name="Plan Code / SKU")
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='plans')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='plans', help_text="Optional linked variant configuration")
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='growth')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Subscription recurring charge")
    trial_days = models.PositiveIntegerField(default=14, help_text="Free trial duration in days")
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
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
            base_slug = slugify(f"{self.product.name}-{self.name}")
            slug = base_slug
            counter = 1
            while SubscriptionPlan.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.product.name} (${self.price}/{self.billing_cycle})"

    @property
    def monthly_equivalent(self):
        """Calculates normalized monthly equivalent for comparison."""
        if self.billing_cycle == 'annual':
            return round(self.price / 12, 2)
        elif self.billing_cycle == 'quarterly':
            return round(self.price / 3, 2)
        return self.price

    @property
    def active_subscribers_count(self):
        """Active subscriptions using this plan."""
        return getattr(self, 'subscriptions', None).filter(status='active').count() if hasattr(self, 'subscriptions') else 0

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
