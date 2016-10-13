from django.conf import settings


def help_urls(request):
    return {
        'GOOGLE_AUTH_HELP_URL': settings.GOOGLE_AUTH_HELP_URL,
    }
