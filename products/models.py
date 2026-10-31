from decimal import Decimal
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator

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
    """SaaS Software Product or Offering."""
    PRODUCT_TYPE_CHOICES = [
        ('software', 'Software Package'),
        ('saas', 'Cloud SaaS Subscription'),
        ('service', 'Professional Service'),
        ('addon', 'Add-on Module'),
        ('hardware', 'Hardware Appliance'),
        ('digital', 'Digital License'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('draft', 'Draft'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=150, verbose_name="Product Name")
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, verbose_name="Product SKU / Code")
    product_type = models.CharField(
        max_length=30,
        choices=PRODUCT_TYPE_CHOICES,
        default='software',
        verbose_name="Product Type"
    )
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    # Financial fields
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Selling Price",
        help_text="Standard selling base price"
    )
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Cost Price",
        help_text="Direct internal cost to produce or deliver"
    )

    tagline = models.CharField(max_length=255, blank=True, help_text="Short marketing punchline")
    description = models.TextField(help_text="Detailed product specification and features")
    notes = models.TextField(blank=True, help_text="Internal administrative and operational notes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created Date")
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
        return f"{self.name} ({self.get_product_type_display()} - {self.sku})"

    # Backward compatibility with base_price
    @property
    def base_price(self):
        return self.selling_price

    @base_price.setter
    def base_price(self, val):
        self.selling_price = val

    @property
    def gross_profit(self):
        """Selling Price minus Cost Price."""
        return max(Decimal('0.00'), self.selling_price - self.cost_price)

    @property
    def profit_margin_percent(self):
        """Profit margin in percent."""
        if self.selling_price > 0:
            return round((self.gross_profit / self.selling_price) * 100, 1)
        return 0.0

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
    """
    Variants of a product with custom additional charge.
    Example:
      Product: Software Package (Base: ₹500)
      Variant Standard: ₹0 additional charge -> Final: ₹500
      Variant Odoo: ₹560 additional charge -> Final: ₹1,060
      Variant Premium: ₹1,000 additional charge -> Final: ₹1,500
    """
    TIER_CHOICES = [
        ('standard', 'Standard Tier'),
        ('odoo', 'Odoo Edition'),
        ('premium', 'Premium / Enterprise'),
        ('custom', 'Custom Solution'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('one_time', 'One-Time / Lifetime'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=150, help_text="e.g. Standard, Odoo, Premium, 10-User Pack")
    sku = models.CharField(max_length=50, unique=True, verbose_name="Variant SKU")
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='standard')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')

    additional_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Additional Charge",
        help_text="Additional surcharge added to the product's selling price"
    )

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
        ordering = ['product', 'additional_charge']
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"

    def __str__(self):
        return f"{self.product.name} - {self.name} (+{self.additional_charge} => {self.final_price})"

    @property
    def base_price(self):
        return self.product.selling_price if self.product else Decimal('0.00')

    @property
    def final_price(self):
        """Calculates final price automatically: Base Selling Price + Additional Charge."""
        base = self.product.selling_price if self.product else Decimal('0.00')
        return base + (self.additional_charge or Decimal('0.00'))

    # Backward compatibility with price
    @property
    def price(self):
        return self.final_price
