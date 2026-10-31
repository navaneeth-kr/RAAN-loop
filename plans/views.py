from django.shortcuts import render

def index(request):
    """Subscription tiers and pricing plans view."""
    plans = [
        {
            'name': 'Starter Plan',
            'product': 'Cloud Platform',
            'price': '$29.00',
            'interval': 'Monthly',
            'features': ['Up to 5 team members', '10 GB Cloud Storage', 'Standard Email Support', 'Basic Analytics'],
            'popular': False,
        },
        {
            'name': 'Pro Business',
            'product': 'Cloud Platform',
            'price': '$99.00',
            'interval': 'Monthly',
            'features': ['Unlimited team members', '250 GB Cloud Storage', '24/7 Priority Support', 'Advanced Security & SSO', 'Automated Backups'],
            'popular': True,
        },
        {
            'name': 'Enterprise Suite',
            'product': 'All-in-One Bundle',
            'price': '$299.00',
            'interval': 'Monthly',
            'features': ['Dedicated account manager', 'Unlimited Storage & API Calls', 'Custom Integrations', '99.99% SLA Guarantee', 'Audit Logs & Compliance'],
            'popular': False,
        },
    ]
    return render(request, 'plans/index.html', {
        'page_title': 'Subscription Plans & Pricing Tiers',
        'active_tab': 'plans',
        'plans': plans,
    })
