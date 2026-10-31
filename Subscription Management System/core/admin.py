from django.contrib import admin
from .models import SystemSetting, ActivityLog

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'currency_code', 'currency_symbol', 'tax_rate', 'updated_at')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'category', 'user', 'timestamp')
    list_filter = ('category', 'timestamp')
    search_fields = ('action', 'details')
