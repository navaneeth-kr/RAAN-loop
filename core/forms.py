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


import re
from django.contrib.auth.models import User
from .models import StaffProfile

class CustomerRegistrationForm(forms.Form):
    """Customer self-service portal registration form meeting Section 3 requirements."""
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name'})
    )
    company_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company / Organization (Optional)'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@company.com'})
    )
    phone = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 000-0000'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create strong password'})
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists. Please sign in.")
        return email

    def clean_password(self):
        pwd = self.cleaned_data.get('password', '')
        # Section 3: > 8 chars, uppercase, lowercase, special char
        if len(pwd) <= 8:
            raise forms.ValidationError("Password must be strictly more than 8 characters long.")
        if not re.search(r'[A-Z]', pwd):
            raise forms.ValidationError("Password must contain at least one uppercase letter (A-Z).")
        if not re.search(r'[a-z]', pwd):
            raise forms.ValidationError("Password must contain at least one lowercase letter (a-z).")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', pwd):
            raise forms.ValidationError("Password must contain at least one special character (!@#$%^&* etc.).")
        return pwd

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned


class StaffCreationForm(forms.Form):
    """Admin form for provisioning staff accounts with role-based access control."""
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'staff@brightloop.io'}))
    role = forms.ChoiceField(choices=StaffProfile.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.CharField(max_length=100, initial="Operations", widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Initial Temporary Password'}))
    is_active = forms.BooleanField(initial=True, required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use by another account.")
        return email


class StaffEditForm(forms.Form):
    """Admin form for updating existing staff credentials and department."""
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(choices=StaffProfile.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    is_active = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
