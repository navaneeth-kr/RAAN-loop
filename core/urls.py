from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('settings/', views.AdminSettingsView.as_view(), name='admin_settings'),
    path('exports/', views.ExportCenterView.as_view(), name='export_center'),
    path('exports/download/', views.ExportDownloadView.as_view(), name='export_download'),
]
