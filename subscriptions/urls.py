from django.urls import path
from . import views

urlpatterns = [
    # Customer Management (Person 1 - Section 4)
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),

    # Subscription Lifecycle Management (Person 3 - Sections 8 & 18)
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscription_list'),
    path('subscriptions/create/', views.SubscriptionCreateView.as_view(), name='subscription_create'),
    path('subscriptions/<int:pk>/', views.SubscriptionDetailView.as_view(), name='subscription_detail'),
    path('subscriptions/<int:pk>/edit/', views.SubscriptionUpdateView.as_view(), name='subscription_update'),
    path('subscriptions/<int:pk>/confirm/', views.SubscriptionConfirmView.as_view(), name='subscription_confirm'),
    path('subscriptions/<int:pk>/activate/', views.SubscriptionActivateView.as_view(), name='subscription_activate'),
    path('subscriptions/<int:pk>/pause/', views.SubscriptionPauseView.as_view(), name='subscription_pause'),
    path('subscriptions/<int:pk>/resume/', views.SubscriptionResumeView.as_view(), name='subscription_resume'),
    path('subscriptions/<int:pk>/cancel/', views.SubscriptionCancelView.as_view(), name='subscription_cancel'),
    path('subscriptions/<int:pk>/renew/', views.SubscriptionRenewView.as_view(), name='subscription_renew'),
    path('subscriptions/<int:pk>/delete/', views.SubscriptionDeleteView.as_view(), name='subscription_delete'),

    # Quotation Management (Person 3 - Section 7)
    path('quotations/', views.QuotationListView.as_view(), name='quotation_list'),
    path('quotations/create/', views.QuotationCreateView.as_view(), name='quotation_create'),
    path('quotations/<int:pk>/', views.QuotationDetailView.as_view(), name='quotation_detail'),
    path('quotations/<int:pk>/edit/', views.QuotationUpdateView.as_view(), name='quotation_update'),
    path('quotations/<int:pk>/convert/', views.QuotationConvertToSubscriptionView.as_view(), name='quotation_convert'),
    path('quotations/<int:pk>/delete/', views.QuotationDeleteView.as_view(), name='quotation_delete'),

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
