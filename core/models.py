from django.db import models
from django.contrib.auth.models import User

class SystemSetting(models.Model):
    """Global SaaS System and Administrative Settings."""
    company_name = models.CharField(max_length=150, default="Brightloop Software")
    support_email = models.EmailField(default="support@brightloop.io")
    billing_email = models.EmailField(default="billing@brightloop.io")
    currency_code = models.CharField(max_length=10, default="USD")
    currency_symbol = models.CharField(max_length=5, default="$")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, help_text="Default tax rate in %")
    default_trial_days = models.PositiveIntegerField(default=14, help_text="Default free trial period in days")
    grace_period_days = models.PositiveIntegerField(default=7, help_text="Grace period after failed payment")
    invoice_prefix = models.CharField(max_length=10, default="BL-INV-")
    maintenance_mode = models.BooleanField(default=False)
    allow_self_signup = models.BooleanField(default=True)
    notify_on_new_subscription = models.BooleanField(default=True)
    notify_on_cancellation = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"{self.company_name} Settings ({self.currency_symbol})"

    @classmethod
    def get_settings(cls):
        """Singleton getter pattern."""
        settings, created = cls.objects.get_or_create(id=1)
        return settings


class ActivityLog(models.Model):
    """System activity and audit trail for SaaS actions."""
    CATEGORY_CHOICES = [
        ('dashboard', 'Dashboard View'),
        ('product', 'Product Management'),
        ('variant', 'Variant Management'),
        ('plan', 'Plan Management'),
        ('setting', 'Settings Update'),
        ('export', 'Data Export'),
        ('system', 'System Event'),
    ]

    action = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='system')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.action} ({self.timestamp:%Y-%m-%d %H:%M})"
