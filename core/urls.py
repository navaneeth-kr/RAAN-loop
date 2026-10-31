from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.AdminLoginView.as_view(), name='admin_login'),
    path('logout/', views.AdminLogoutView.as_view(), name='admin_logout'),
    path('staff/', views.StaffListView.as_view(), name='staff_list'),
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('settings/', views.AdminSettingsView.as_view(), name='admin_settings'),
    path('exports/', views.ExportCenterView.as_view(), name='export_center'),
    path('exports/download/', views.ExportDownloadView.as_view(), name='export_download'),
    path('exports/backup/', views.DatabaseBackupView.as_view(), name='database_backup'),
]

