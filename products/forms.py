from django import forms
from .models import Product, ProductCategory, ProductVariant

class ProductForm(forms.ModelForm):
    """Form to create and edit products."""
    class Meta:
        model = Product
        fields = [
            'name',
            'sku',
            'category',
            'tagline',
            'description',
            'base_price',
            'status',
            'is_featured',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cloud Sentinel Suite'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BL-CSS-01'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enterprise cloud security and telemetry'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Comprehensive product overview...'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductVariantForm(forms.ModelForm):
    """Form to manage variants tied to products."""
    class Meta:
        model = ProductVariant
        fields = [
            'product',
            'name',
            'sku',
            'tier',
            'billing_cycle',
            'price',
            'setup_fee',
            'max_users',
            'storage_gb',
            'api_rate_limit',
            'sla_support_level',
            'description',
            'is_active',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Pro Dedicated Instance'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BL-VAR-PRO-01'}),
            'tier': forms.Select(attrs={'class': 'form-select'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'setup_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_users': forms.NumberInput(attrs={'class': 'form-control'}),
            'storage_gb': forms.NumberInput(attrs={'class': 'form-control'}),
            'api_rate_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'sla_support_level': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 24/7 Dedicated Slack Channel'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductCategoryForm(forms.ModelForm):
    """Form to manage product categories."""
    class Meta:
        model = ProductCategory
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Developer Tools'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-cloud-arrow-up'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
