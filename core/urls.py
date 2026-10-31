from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Auth
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.AdminLoginView.as_view(), name='admin_login'),
    path('register/', views.CustomerRegisterView.as_view(), name='customer_register'),
    path('logout/', views.AdminLogoutView.as_view(), name='admin_logout'),

    # Staff Management (Person 1 - Section 15)
    path('staff/', views.StaffListView.as_view(), name='staff_list'),
    path('staff/create/', views.StaffCreateView.as_view(), name='staff_create'),
    path('staff/<int:pk>/edit/', views.StaffUpdateView.as_view(), name='staff_update'),
    path('staff/<int:pk>/toggle/', views.StaffToggleActiveView.as_view(), name='staff_toggle_active'),

    # Audit Trail (Person 1 - Section 21)
    path('audit-logs/', views.ActivityLogListView.as_view(), name='activity_logs'),

    # In-App Notifications (Person 3 - Section 20)
    path('notifications/', views.NotificationListView.as_view(), name='notification_list'),
    path('notifications/<int:pk>/read/', views.NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('notifications/mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),

    # Customer Self-Service Portal (Person 3 - Section 14)
    path('portal/', views.CustomerDashboardView.as_view(), name='customer_portal'),
    path('portal/subscriptions/<int:pk>/', views.CustomerSubscriptionDetailView.as_view(), name='portal_subscription_detail'),
    path('portal/invoices/<int:pk>/', views.CustomerInvoiceDetailView.as_view(), name='portal_invoice_detail'),
    path('portal/payments/', views.CustomerPaymentListView.as_view(), name='portal_payment_list'),
    path('portal/profile/', views.CustomerProfileView.as_view(), name='customer_profile'),

    # PDF Generation Endpoints (Person 4 & Section 19)
    path('invoices/<int:pk>/pdf/', views.InvoicePDFDownloadView.as_view(), name='invoice_pdf_download'),
    path('quotations/<int:pk>/pdf/', views.QuotationPDFDownloadView.as_view(), name='quotation_pdf_download'),
    path('payments/<int:pk>/pdf/', views.PaymentReceiptPDFDownloadView.as_view(), name='payment_receipt_pdf_download'),

    # Reports, Settings & Exports
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('settings/', views.AdminSettingsView.as_view(), name='admin_settings'),
    path('exports/', views.ExportCenterView.as_view(), name='export_center'),
    path('exports/download/', views.ExportDownloadView.as_view(), name='export_download'),
    path('exports/backup/', views.DatabaseBackupView.as_view(), name='database_backup'),
]

