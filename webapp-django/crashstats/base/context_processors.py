from django.core.urlresolvers import reverse
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


def browserid(request):
    # by making this a function, it means we only need to run this
    # when ``redirect_next()`` is called
    def redirect_next():
        if request.GET.get('next'):
            return request.GET.get('next')
        absolute_url = request.build_absolute_uri()
        if reverse('crashstats.login') in absolute_url:
            # can't have that!
            absolute_url = reverse(
                'crashstats.home',
                args=(settings.DEFAULT_PRODUCT,)
            )
        return absolute_url
    return {'redirect_next': redirect_next}
