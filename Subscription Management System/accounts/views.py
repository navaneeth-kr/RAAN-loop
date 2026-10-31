from django.shortcuts import render

def index(request):
    """Customer accounts directory and management foundation view."""
    accounts_list = [
        {'name': 'Apex Digital Media', 'email': 'billing@apexdigital.io', 'subs': 2, 'joined': 'Jan 15, 2026', 'status': 'Active'},
        {'name': 'BlueSky Technologies', 'email': 'ops@bluesky.tech', 'subs': 1, 'joined': 'Mar 22, 2026', 'status': 'Active'},
        {'name': 'Omni Logistics Inc.', 'email': 'finance@omnilogistics.com', 'subs': 3, 'joined': 'Apr 05, 2026', 'status': 'Warning'},
        {'name': 'NextWave Studio', 'email': 'hello@nextwave.design', 'subs': 1, 'joined': 'Jul 12, 2026', 'status': 'Active'},
        {'name': 'Zenith Health AI', 'email': 'accounts@zenithhealth.ai', 'subs': 1, 'joined': 'Sep 09, 2026', 'status': 'Overdue'},
    ]
    return render(request, 'accounts/index.html', {
        'page_title': 'Customer Accounts Directory',
        'active_tab': 'accounts',
        'accounts': accounts_list,
    })
