from django.conf import settings


def google_analytics(request):
    return {
        'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', None),
        'GOOGLE_ANALYTICS_DOMAIN': getattr(
            settings,
            'GOOGLE_ANALYTICS_DOMAIN',
            'auto'
        )
    }
