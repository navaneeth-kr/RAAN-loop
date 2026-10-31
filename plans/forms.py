from django import forms
from .models import SubscriptionPlan, PlanFeature

class SubscriptionPlanForm(forms.ModelForm):
    """Form to manage subscription plans."""
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
            'trial_days',
            'setup_fee',
            'status',
            'is_featured',
            'sort_order',
            'description',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Growth Tier Plan'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PLAN-GROWTH-MO'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'variant': forms.Select(attrs={'class': 'form-select'}),
            'tier': forms.Select(attrs={'class': 'form-select'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'trial_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'setup_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Key plan features and pricing benefits'}),
        }


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
