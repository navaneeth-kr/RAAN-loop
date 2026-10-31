from django.urls import path
from . import views

urlpatterns = [
    # Customer & Subscription Existing Routes
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscription_list'),
    path('quotations/', views.QuotationListView.as_view(), name='quotation_list'),

    # Person 4: Invoice Management
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='invoice_update'),
    path('invoices/<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/<int:pk>/mark-paid/', views.InvoiceMarkPaidView.as_view(), name='invoice_mark_paid'),
    path('invoices/calculate-preview/', views.InvoiceCalculatePreviewView.as_view(), name='invoice_calculate_preview'),

    # Person 4: Discount Management
    path('discounts/', views.DiscountListView.as_view(), name='discount_list'),
    path('discounts/create/', views.DiscountCreateView.as_view(), name='discount_create'),
    path('discounts/<int:pk>/edit/', views.DiscountUpdateView.as_view(), name='discount_update'),
    path('discounts/<int:pk>/delete/', views.DiscountDeleteView.as_view(), name='discount_delete'),
    path('discounts/<int:pk>/toggle/', views.DiscountToggleStatusView.as_view(), name='discount_toggle_status'),

    # Person 4: Payment Management
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('payments/<int:pk>/refund/', views.PaymentRefundView.as_view(), name='payment_refund'),

    # Person 4: Tax Configuration
    path('taxes/', views.TaxConfigurationView.as_view(), name='tax_configuration'),
    path('taxes/<int:pk>/default/', views.TaxRateSetDefaultView.as_view(), name='tax_set_default'),
    path('taxes/<int:pk>/delete/', views.TaxRateDeleteView.as_view(), name='tax_delete'),
]
