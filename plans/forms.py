from decimal import Decimal
from django import forms
from .models import SubscriptionPlan, PlanFeature

class SubscriptionPlanForm(forms.ModelForm):
    """
    Form to create and edit subscription plans with rigorous date validations,
    pricing rules, quantity controls, and policy toggles.
    """
    class Meta:
        model = SubscriptionPlan
        fields = [
            'name',
            'code',
            'product',
            'variant',
            'tier',
            'billing_cycle',
            'price',
            'min_quantity',
            'start_date',
            'end_date',
            'auto_close',
            'allow_early_cancellation',
            'allow_pausing',
            'allow_renewal',
            'trial_days',
            'setup_fee',
            'status',
            'is_featured',
            'sort_order',
            'description',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Software Package (Standard Tier)'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PLAN-SW-STD-500'}),
            'product': forms.Select(attrs={'class': 'form-select', 'id': 'plan_product_select'}),
            'variant': forms.Select(attrs={'class': 'form-select', 'id': 'plan_variant_select'}),
            'tier': forms.Select(attrs={'class': 'form-select'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'id': 'plan_unit_price', 'placeholder': '500.00'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'id': 'plan_min_quantity', 'placeholder': '1'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'plan_start_date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'plan_end_date'}),
            'auto_close': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'plan_auto_close'}),
            'allow_early_cancellation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_pausing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_renewal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'trial_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'setup_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Key plan features, usage rights, and quota terms'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price <= Decimal('0.00'):
            raise forms.ValidationError("Plan unit price must be greater than zero.")
        return price

    def clean_min_quantity(self):
        min_qty = self.cleaned_data.get('min_quantity')
        if min_qty is None or min_qty < 1:
            raise forms.ValidationError("Minimum quantity must be at least 1.")
        return min_qty

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        auto_close = cleaned_data.get('auto_close')

        # 1. Date Validation: End Date cannot be earlier than Start Date
        if start_date and end_date:
            if end_date < start_date:
                self.add_error('end_date', "End date cannot be earlier than start date.")

        # 2. Policy Validation: Automatic Closure requires an End Date
        if auto_close and not end_date:
            self.add_error('end_date', "An End Date is required when Automatic Closure is enabled.")

        return cleaned_data


class PlanFeatureForm(forms.ModelForm):
    """Form to add or edit features for a subscription plan."""
    class Meta:
        model = PlanFeature
        fields = ['name', 'quota_value', 'is_included', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Max Active Workflows'}),
            'quota_value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Unlimited or 50'}),
            'is_included': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
