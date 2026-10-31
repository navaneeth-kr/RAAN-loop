from django import forms
from .models import SystemSetting

class SystemSettingForm(forms.ModelForm):
    """Admin settings configuration form with Bootstrap 5 widgets."""
    class Meta:
        model = SystemSetting
        fields = [
            'company_name',
            'support_email',
            'billing_email',
            'currency_code',
            'currency_symbol',
            'tax_rate',
            'default_trial_days',
            'grace_period_days',
            'invoice_prefix',
            'maintenance_mode',
            'allow_self_signup',
            'notify_on_new_subscription',
            'notify_on_cancellation',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Brightloop Software'}),
            'support_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'support@brightloop.io'}),
            'billing_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'billing@brightloop.io'}),
            'currency_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'USD'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '$'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'default_trial_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'grace_period_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'invoice_prefix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'BL-INV-'}),
            'maintenance_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_self_signup': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_new_subscription': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_cancellation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
