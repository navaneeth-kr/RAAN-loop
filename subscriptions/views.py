from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.db.models import Q, Sum
from core.utils import paginate_queryset
from .models import Customer, Subscription, Invoice, Payment, Quotation, Discount

class CustomerListView(View):
    """List and search customers."""
    template_name = 'subscriptions/customer_list.html'

    def get(self, request):
        queryset = Customer.objects.all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(full_name__icontains=q) |
                Q(company_name__icontains=q) |
                Q(email__icontains=q) |
                Q(country__icontains=q)
            )
        status = request.GET.get('status')
        if status in ['active', 'inactive', 'suspended']:
            queryset = queryset.filter(status=status)

        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'customers': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'page_title': 'Customers Management',
        }
        return render(request, self.template_name, context)


class SubscriptionListView(View):
    """List customer subscriptions with search and filtering."""
    template_name = 'subscriptions/subscription_list.html'

    def get(self, request):
        queryset = Subscription.objects.select_related('customer', 'plan').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(subscription_id__icontains=q) |
                Q(customer__full_name__icontains=q) |
                Q(customer__email__icontains=q) |
                Q(plan__name__icontains=q)
            )
        status = request.GET.get('status')
        if status in ['active', 'trialing', 'past_due', 'canceled']:
            queryset = queryset.filter(status=status)

        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'subscriptions': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'page_title': 'Subscription Lifecycle Management',
        }
        return render(request, self.template_name, context)


class QuotationListView(View):
    """List and manage quotations."""
    template_name = 'subscriptions/quotation_list.html'

    def get(self, request):
        queryset = Quotation.objects.select_related('customer', 'plan').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(quotation_number__icontains=q) |
                Q(customer__full_name__icontains=q)
            )
        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'quotations': page_obj.object_list,
            'search_query': q,
            'page_title': 'Quotations Management',
        }
        return render(request, self.template_name, context)


class InvoiceListView(View):
    """List invoices with status highlights."""
    template_name = 'subscriptions/invoice_list.html'

    def get(self, request):
        queryset = Invoice.objects.select_related('customer', 'subscription').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(invoice_number__icontains=q) |
                Q(customer__full_name__icontains=q)
            )
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'invoices': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'page_title': 'Invoices & Billing',
        }
        return render(request, self.template_name, context)


class DiscountListView(View):
    """List promotional discounts and coupons."""
    template_name = 'subscriptions/discount_list.html'

    def get(self, request):
        queryset = Discount.objects.all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(code__icontains=q) |
                Q(description__icontains=q)
            )
        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'discounts': page_obj.object_list,
            'search_query': q,
            'page_title': 'Discounts & Promotions',
        }
        return render(request, self.template_name, context)


class PaymentListView(View):
    """List and audit payments."""
    template_name = 'subscriptions/payment_list.html'

    def get(self, request):
        queryset = Payment.objects.select_related('customer', 'invoice').all()
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(payment_id__icontains=q) |
                Q(customer__full_name__icontains=q) |
                Q(transaction_reference__icontains=q)
            )
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        page_obj = paginate_queryset(request, queryset, per_page=10)
        context = {
            'page_obj': page_obj,
            'payments': page_obj.object_list,
            'search_query': q,
            'selected_status': status,
            'page_title': 'Payments & Transaction Log',
        }
        return render(request, self.template_name, context)


def index(request):
    """Customer subscription lifecycle directory view."""
    subs = [
        {'id': 'SUB-1089', 'client': 'Apex Digital Media', 'plan': 'Pro Business', 'amount': '$99.00', 'status': 'Active', 'renewal': 'Nov 30, 2026'},
        {'id': 'SUB-1088', 'client': 'BlueSky Technologies', 'plan': 'Enterprise Suite', 'amount': '$3,588.00', 'status': 'Active', 'renewal': 'Oct 29, 2027'},
        {'id': 'SUB-1087', 'client': 'Omni Logistics Inc.', 'plan': 'Pro Business', 'amount': '$99.00', 'status': 'Pending', 'renewal': 'Nov 28, 2026'},
        {'id': 'SUB-1086', 'client': 'NextWave Studio', 'plan': 'Starter Plan', 'amount': '$29.00', 'status': 'Active', 'renewal': 'Nov 27, 2026'},
    ]
    return render(request, 'subscriptions/index.html', {
        'page_title': 'Subscriptions Management',
        'active_tab': 'subscriptions',
        'subscriptions': subs,
    })
