from decimal import Decimal
from django import forms
from .models import Product, ProductCategory, ProductVariant

class ProductForm(forms.ModelForm):
    """Admin form to create and edit products with price validation."""
    class Meta:
        model = Product
        fields = [
            'name',
            'product_type',
            'sku',
            'category',
            'selling_price',
            'cost_price',
            'tagline',
            'description',
            'notes',
            'status',
            'is_featured',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Software Package, Cloud Suite'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BL-PKG-500'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': '500.00'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00', 'placeholder': '250.00'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short commercial tagline'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product features and specification...'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Internal administrative notes, vendor details, or margin rules'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_selling_price(self):
        selling = self.cleaned_data.get('selling_price')
        if selling is None or selling <= Decimal('0.00'):
            raise forms.ValidationError("Selling price must be greater than zero.")
        return selling

    def clean_cost_price(self):
        cost = self.cleaned_data.get('cost_price')
        if cost is not None and cost < Decimal('0.00'):
            raise forms.ValidationError("Cost price cannot be negative.")
        return cost

    def clean(self):
        cleaned_data = super().clean()
        selling = cleaned_data.get('selling_price')
        cost = cleaned_data.get('cost_price')

        if selling and cost and cost > selling:
            self.add_error('cost_price', f"Cost price (${cost}) exceeds selling price (${selling}). Negative profit margin.")
        return cleaned_data


class ProductVariantForm(forms.ModelForm):
    """Form to manage product variants and additional surcharges."""
    class Meta:
        model = ProductVariant
        fields = [
            'product',
            'name',
            'sku',
            'tier',
            'billing_cycle',
            'additional_charge',
            'max_users',
            'storage_gb',
            'api_rate_limit',
            'sla_support_level',
            'description',
            'is_active',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select', 'id': 'variant_product_select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard, Odoo, Premium'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BL-VAR-ODOO-560'}),
            'tier': forms.Select(attrs={'class': 'form-select'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'additional_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00', 'id': 'variant_add_charge', 'placeholder': '0.00, 560.00, 1000.00'}),
            'max_users': forms.NumberInput(attrs={'class': 'form-control'}),
            'storage_gb': forms.NumberInput(attrs={'class': 'form-control'}),
            'api_rate_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'sla_support_level': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_additional_charge(self):
        charge = self.cleaned_data.get('additional_charge')
        if charge is not None and charge < Decimal('0.00'):
            raise forms.ValidationError("Additional charge cannot be negative.")
        return charge or Decimal('0.00')


class ProductCategoryForm(forms.ModelForm):
    """Category form."""
    class Meta:
        model = ProductCategory
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
