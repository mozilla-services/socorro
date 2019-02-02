from django.conf import settings as django_settings


def settings(request):
    return {
        'SETTINGS': django_settings,
        'DEBUG': django_settings.DEBUG,
        'GOOGLE_ANALYTICS_ID': django_settings.GOOGLE_ANALYTICS_ID,
    }
