from django.urls import path
from . import views

urlpatterns = [
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscription_list'),
    path('quotations/', views.QuotationListView.as_view(), name='quotation_list'),
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('discounts/', views.DiscountListView.as_view(), name='discount_list'),
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
]
