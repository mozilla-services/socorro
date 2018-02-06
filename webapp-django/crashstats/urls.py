import os

from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from django.views.static import serve

from .base.monkeypatches import patch
from .crashstats import urls
from .supersearch import urls as supersearch_urls
from .authentication import urls as auth_urls
from .monitoring import urls as monitoring_urls


patch()

handler500 = 'crashstats.base.views.handler500'
handler404 = 'crashstats.base.views.handler404'


urlpatterns = [
    url(r'^(?P<path>contribute\.json)$', serve, {
        'document_root': os.path.join(settings.ROOT, '..'),
    }),
    url(r'^(?P<path>favicon\.ico)$', serve, {
        'document_root': os.path.join(settings.ROOT, 'crashstats', 'base', 'static', 'img'),
    }),
    url(r'', include(urls, namespace='crashstats')),
    url(r'', include(supersearch_urls)),
    url(r'^signature/', include(
        'crashstats.signature.urls',
        namespace='signature'
    )),
    url(r'^topcrashers/', include(
        'crashstats.topcrashers.urls',
        namespace='topcrashers'
    )),
    url(r'^sources/', include(
        'crashstats.sources.urls',
        namespace='sources'
    )),
    url(r'^home/', include(
        'crashstats.home.urls',
        namespace='home'
    )),
    url(r'', include(auth_urls, namespace='auth')),
    url(r'^monitoring/', include(monitoring_urls, namespace='monitoring')),
    url(r'^api/tokens/', include('crashstats.tokens.urls', namespace='tokens')),
    url(r'^api/', include('crashstats.api.urls', namespace='api')),
    # redirect all symbols/ requests to Tecken
    url(r'^symbols/.*',
        RedirectView.as_view(url='https://symbols.mozilla.org/'),
        name='redirect-to-tecken'),
    # if we ever use the Django admin we might want to change this URL
    url(r'^admin/', include('crashstats.manage.urls', namespace='manage')),
    url(r'^profile/', include(
        'crashstats.profile.urls',
        namespace='profile'
    )),
    url(r'^documentation/', include(
        'crashstats.documentation.urls',
        namespace='documentation'
    )),
]

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
