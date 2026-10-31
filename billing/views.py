from django.shortcuts import render

def index(request):
    """Invoices and billing records view."""
    invoices = [
        {'invoice_num': 'INV-2026-001', 'client': 'Apex Digital Media', 'amount': '$99.00', 'issue_date': 'Oct 15, 2026', 'due_date': 'Oct 30, 2026', 'status': 'Paid'},
        {'invoice_num': 'INV-2026-002', 'client': 'BlueSky Technologies', 'amount': '$3,588.00', 'issue_date': 'Oct 20, 2026', 'due_date': 'Nov 04, 2026', 'status': 'Paid'},
        {'invoice_num': 'INV-2026-003', 'client': 'Omni Logistics Inc.', 'amount': '$99.00', 'issue_date': 'Oct 22, 2026', 'due_date': 'Nov 06, 2026', 'status': 'Pending'},
        {'invoice_num': 'INV-2026-004', 'client': 'NextWave Studio', 'amount': '$29.00', 'issue_date': 'Oct 25, 2026', 'due_date': 'Nov 09, 2026', 'status': 'Paid'},
        {'invoice_num': 'INV-2026-005', 'client': 'Zenith Health AI', 'amount': '$3,588.00', 'issue_date': 'Sep 25, 2026', 'due_date': 'Oct 10, 2026', 'status': 'Overdue'},
    ]
    return render(request, 'billing/index.html', {
        'page_title': 'Invoices & Billing',
        'active_tab': 'billing',
        'invoices': invoices,
    })
