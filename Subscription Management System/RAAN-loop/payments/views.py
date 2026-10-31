from django.shortcuts import render

def index(request):
    """Payment transactions and gateway logs foundation view."""
    transactions = [
        {'txn_id': 'TXN-99824', 'gateway': 'Stripe', 'customer': 'Apex Digital Media', 'amount': '$99.00', 'status': 'Succeeded', 'date': '2026-10-15 14:22'},
        {'txn_id': 'TXN-99825', 'gateway': 'Stripe (ACH)', 'customer': 'BlueSky Technologies', 'amount': '$3,588.00', 'status': 'Succeeded', 'date': '2026-10-20 09:10'},
        {'txn_id': 'TXN-99826', 'gateway': 'PayPal', 'customer': 'NextWave Studio', 'amount': '$29.00', 'status': 'Succeeded', 'date': '2026-10-25 18:45'},
        {'txn_id': 'TXN-99827', 'gateway': 'Stripe', 'customer': 'Zenith Health AI', 'amount': '$3,588.00', 'status': 'Failed (Insufficient Funds)', 'date': '2026-10-26 11:02'},
    ]
    return render(request, 'payments/index.html', {
        'page_title': 'Payments & Gateway Transactions',
        'active_tab': 'payments',
        'transactions': transactions,
    })
