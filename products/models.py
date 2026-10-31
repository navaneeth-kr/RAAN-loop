from django.db import models
from django.utils.text import slugify

class ProductCategory(models.Model):
    """Categorization for Brightloop products."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="bi-box-seam", help_text="Bootstrap Icon class name")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def product_count(self):
        return self.products.count()


class Product(models.Model):
    """SaaS Software Product or Core Offering."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('draft', 'Draft'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, verbose_name="Product SKU / Code")
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    tagline = models.CharField(max_length=255, blank=True, help_text="Short marketing punchline")
    description = models.TextField(help_text="Detailed product specification and overview")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Starting base price")
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def variant_count(self):
        return self.variants.count()

    @property
    def active_plans_count(self):
        return self.plans.filter(status='active').count()

    @property
    def badge_class(self):
        mapping = {
            'active': 'success',
            'draft': 'warning',
            'archived': 'secondary',
        }
        return mapping.get(self.status, 'primary')


class ProductVariant(models.Model):
    """Variants of a product (e.g. Editions, Cloud vs Dedicated, Seat Packs)."""
    TIER_CHOICES = [
        ('standard', 'Standard Tier'),
        ('pro', 'Professional Tier'),
        ('enterprise', 'Enterprise Tier'),
        ('custom', 'Custom Solution'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual (Save ~20%)'),
        ('lifetime', 'One-Time / Lifetime'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=150, help_text="e.g. Professional Cloud, 10-User Seat Pack")
    sku = models.CharField(max_length=50, unique=True, verbose_name="Variant SKU")
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='standard')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Recurring price for this variant")
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Feature Quotas & Specifications
    max_users = models.PositiveIntegerField(default=5, help_text="Max allowed team seats")
    storage_gb = models.PositiveIntegerField(default=50, help_text="Included cloud storage in GB")
    api_rate_limit = models.PositiveIntegerField(default=10000, help_text="API calls per 24 hours")
    sla_support_level = models.CharField(max_length=100, default="Standard Email (48h)", help_text="SLA response time")
    
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product', 'price']
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"

    def __str__(self):
        return f"{self.product.name} - {self.name} (${self.price}/{self.billing_cycle})"

    @property
    def tier_badge_class(self):
        mapping = {
            'standard': 'info',
            'pro': 'primary',
            'enterprise': 'purple',
            'custom': 'dark',
        }
        return mapping.get(self.tier, 'secondary')
