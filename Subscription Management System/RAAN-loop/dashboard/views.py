from django.shortcuts import render

def index(request):
    """
    Main SaaS Dashboard view presenting key subscription metrics,
    revenue trends, and recent customer activities.
    """
    context = {
        'page_title': 'SaaS Dashboard Overview',
        'company_name': 'Brightloop Software',
        'active_tab': 'dashboard',
        'metrics': {
            'mrr': '$34,850',
            'mrr_growth': '+12.4%',
            'active_subscriptions': '1,280',
            'sub_growth': '+8.2%',
            'churn_rate': '1.6%',
            'churn_trend': '-0.3%',
            'pending_invoices': '$2,450',
            'pending_count': 9,
        },
        'plans_summary': [
            {'name': 'Starter Plan', 'users': 450, 'price': '$29/mo', 'status': 'Popular'},
            {'name': 'Pro Business', 'users': 620, 'price': '$99/mo', 'status': 'Highest Revenue'},
            {'name': 'Enterprise Suite', 'users': 210, 'price': '$299/mo', 'status': 'Custom SLA'},
        ],
        'recent_subscriptions': [
            {
                'id': 'SUB-1089',
                'customer': 'Apex Digital Media',
                'email': 'billing@apexdigital.io',
                'plan': 'Pro Business',
                'billing_cycle': 'Monthly',
                'amount': '$99.00',
                'status': 'Active',
                'status_class': 'badge-success',
                'date': 'Oct 30, 2026',
            },
            {
                'id': 'SUB-1088',
                'customer': 'BlueSky Technologies',
                'email': 'ops@bluesky.tech',
                'plan': 'Enterprise Suite',
                'billing_cycle': 'Annual',
                'amount': '$3,588.00',
                'status': 'Active',
                'status_class': 'badge-success',
                'date': 'Oct 29, 2026',
            },
            {
                'id': 'SUB-1087',
                'customer': 'Omni Logistics Inc.',
                'email': 'finance@omnilogistics.com',
                'plan': 'Pro Business',
                'billing_cycle': 'Monthly',
                'amount': '$99.00',
                'status': 'Pending Payment',
                'status_class': 'badge-warning',
                'date': 'Oct 28, 2026',
            },
            {
                'id': 'SUB-1086',
                'customer': 'NextWave Studio',
                'email': 'hello@nextwave.design',
                'plan': 'Starter Plan',
                'billing_cycle': 'Monthly',
                'amount': '$29.00',
                'status': 'Active',
                'status_class': 'badge-success',
                'date': 'Oct 27, 2026',
            },
            {
                'id': 'SUB-1085',
                'customer': 'Zenith Health AI',
                'email': 'accounts@zenithhealth.ai',
                'plan': 'Enterprise Suite',
                'billing_cycle': 'Annual',
                'amount': '$3,588.00',
                'status': 'Past Due',
                'status_class': 'badge-danger',
                'date': 'Oct 26, 2026',
            },
        ]
    }
    return render(request, 'dashboard/foundation_index.html', context)
