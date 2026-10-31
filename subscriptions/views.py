from django.shortcuts import render

def index(request):
    """Customer subscriptions lifecycle management view."""
    subscriptions = [
        {'id': 'SUB-1089', 'client': 'Apex Digital Media', 'plan': 'Pro Business', 'started': '2026-01-15', 'renew_date': '2026-11-15', 'status': 'Active'},
        {'id': 'SUB-1088', 'client': 'BlueSky Technologies', 'plan': 'Enterprise Suite', 'started': '2026-03-22', 'renew_date': '2027-03-22', 'status': 'Active'},
        {'id': 'SUB-1087', 'client': 'Omni Logistics Inc.', 'plan': 'Pro Business', 'started': '2026-04-05', 'renew_date': '2026-11-05', 'status': 'Pending'},
        {'id': 'SUB-1086', 'client': 'NextWave Studio', 'plan': 'Starter Plan', 'started': '2026-07-12', 'renew_date': '2026-11-12', 'status': 'Active'},
        {'id': 'SUB-1085', 'client': 'Zenith Health AI', 'plan': 'Enterprise Suite', 'started': '2026-09-09', 'renew_date': '2026-10-09', 'status': 'Past Due'},
    ]
    return render(request, 'subscriptions/index.html', {
        'page_title': 'Subscription Management',
        'active_tab': 'subscriptions',
        'subscriptions': subscriptions,
    })
