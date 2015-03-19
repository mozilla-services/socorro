import os

from django.conf import settings
from django.conf.urls import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .crashstats import urls
from .supersearch import urls as supersearch_urls
from .auth import urls as auth_urls

from funfactory.monkeypatches import patch
patch()

handler500 = 'crashstats.base.views.handler500'
handler404 = 'crashstats.base.views.handler404'


urlpatterns = patterns(
    '',
    (r'^(?P<path>contribute\.json)$', 'django.views.static.serve',
     {'document_root': os.path.join(settings.ROOT, '..')}),
    (r'', include(urls, namespace='crashstats')),
    (r'', include(supersearch_urls)),
    (r'^signature/', include(
        'crashstats.signature.urls',
        namespace='signature'
    )),
    (r'', include(auth_urls, namespace='auth')),
    (r'^api/tokens/', include('crashstats.tokens.urls', namespace='tokens')),
    (r'^api/', include('crashstats.api.urls', namespace='api')),
    (r'^symbols/', include('crashstats.symbols.urls', namespace='symbols')),
    # if we ever use the Django admin we might want to change this URL
    (r'^admin/', include('crashstats.manage.urls', namespace='manage')),
    (r'', include('django_browserid.urls')),
)

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
