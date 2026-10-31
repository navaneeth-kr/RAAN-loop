from .models import SystemSetting

def global_settings(request):
    """Context processor providing system settings to all templates."""
    try:
        settings = SystemSetting.get_settings()
    except Exception:
        settings = None
    return {
        'system_settings': settings,
        'app_name': 'Brightloop Software',
    }
