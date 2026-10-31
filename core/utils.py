import csv
import json
from decimal import Decimal
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from products.models import Product, ProductVariant
from plans.models import SubscriptionPlan
from subscriptions.models import Customer, Subscription, Invoice, Payment, Quotation, Discount

def get_dashboard_metrics(start_date=None, end_date=None, search_query=None):
    """
    Fetches real SaaS metrics directly from the database for the 6 executive cards,
    interactive Chart.js graphs, and recent transactional feeds.
    """
    today = timezone.now().date()
    
    # 1. Total Customers
    customers_qs = Customer.objects.all()
    if search_query:
        customers_qs = customers_qs.filter(
            Q(full_name__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    total_customers = customers_qs.count()

    # 2. Total Products
    total_products = Product.objects.count()
    active_products = Product.objects.filter(status='active').count()

    # 3. Active Subscriptions
    subs_qs = Subscription.objects.all()
    active_subs_count = subs_qs.filter(status='active').count()
    trialing_subs_count = subs_qs.filter(status='trialing').count()

    # 4. Total Revenue (From completed payments / paid invoices)
    payments_qs = Payment.objects.filter(status='completed')
    if start_date:
        payments_qs = payments_qs.filter(payment_date__date__gte=start_date)
    if end_date:
        payments_qs = payments_qs.filter(payment_date__date__lte=end_date)
        
    revenue_sum = payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # If payments table has lower revenue in initial seed, sum paid invoices
    invoices_paid_sum = Invoice.objects.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_revenue = max(revenue_sum, invoices_paid_sum)

    # 5. Pending Payments (Pending transaction count & total value)
    pending_payments_qs = Payment.objects.filter(status='pending')
    pending_payments_count = pending_payments_qs.count()
    pending_payments_amount = pending_payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 6. Overdue Invoices (Count and sum of unpaid invoices past due date)
    overdue_invoices_qs = Invoice.objects.filter(
        Q(status='overdue') | Q(status='pending', due_date__lt=today)
    ).select_related('customer')
    overdue_invoices_count = overdue_invoices_qs.count()
    overdue_invoices_amount = overdue_invoices_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Overdue invoice list with days overdue
    overdue_invoice_list = []
    for inv in overdue_invoices_qs.order_by('due_date')[:6]:
        days_overdue = (today - inv.due_date).days if inv.due_date < today else 0
        overdue_invoice_list.append({
            'invoice': inv,
            'days_overdue': days_overdue,
        })

    # Recent Subscriptions
    recent_subscriptions = Subscription.objects.select_related('customer', 'plan').order_by('-created_at')[:6]

    # Recent Payments
    recent_payments = Payment.objects.select_related('customer', 'invoice').order_by('-payment_date')[:6]

    # Revenue Chart: Last 6 Months Chronological Inflow
    months_labels = []
    revenue_data = []
    for i in range(5, -1, -1):
        target_month_date = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        months_labels.append(target_month_date.strftime('%b %Y'))

        m_start = target_month_date
        if target_month_date.month == 12:
            m_end = target_month_date.replace(year=target_month_date.year + 1, month=1, day=1)
        else:
            m_end = target_month_date.replace(month=target_month_date.month + 1, day=1)

        m_rev = Payment.objects.filter(
            status='completed',
            payment_date__date__gte=m_start,
            payment_date__date__lt=m_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        if m_rev == 0:
            # Fallback to paid invoices for historical month
            m_rev = Invoice.objects.filter(
                status='paid',
                issued_date__gte=m_start,
                issued_date__lt=m_end
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        revenue_data.append(float(m_rev))

    # Subscription Distribution Data
    status_distribution = {
        'labels': ['Active', 'Trialing', 'Past Due', 'Canceled'],
        'data': [
            active_subs_count,
            trialing_subs_count,
            subs_qs.filter(status='past_due').count(),
            subs_qs.filter(status='canceled').count()
        ],
    }

    return {
        # The 6 Primary Dashboard Cards
        'total_customers': total_customers,
        'total_products': total_products,
        'active_products': active_products,
        'active_subscriptions': active_subs_count,
        'trialing_subscriptions': trialing_subs_count,
        'total_revenue': total_revenue,
        'pending_payments_count': pending_payments_count,
        'pending_payments_amount': pending_payments_amount,
        'overdue_invoices_count': overdue_invoices_count,
        'overdue_invoices_amount': overdue_invoices_amount,
        
        # Lists
        'recent_subscriptions': recent_subscriptions,
        'recent_payments': recent_payments,
        'overdue_invoice_list': overdue_invoice_list,

        # Chart.js Ready Payloads
        'chart_revenue': {
            'labels': months_labels,
            'data': revenue_data,
        },
        'chart_status': status_distribution,
    }


def paginate_queryset(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)
    return page_obj
