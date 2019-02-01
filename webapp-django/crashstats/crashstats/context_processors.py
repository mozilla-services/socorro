from django.conf import settings as django_settings


def settings(request):
    return {
        'DEBUG': django_settings.DEBUG,
        'GOOGLE_ANALYTICS_ID': django_settings.GOOGLE_ANALYTICS_ID,
    }
