from django.conf import settings
from django.conf.urls.defaults import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .crashstats import urls
from .supersearch import urls as supersearch_urls

from funfactory.monkeypatches import patch
patch()

handler500 = 'crashstats.base.views.handler500'
handler404 = 'crashstats.base.views.handler404'

# funfactory puts the more limited CompressorExtension extension in
# but we need the one from jingo_offline_compressor.jinja2ext otherwise we
# might an error like this:
#
#    AttributeError: 'CompressorExtension' object has no attribute 'nodelist'
#
from jingo_offline_compressor.jinja2ext import CompressorExtension
import jingo
try:
    jingo.env.extensions.pop(
        'compressor.contrib.jinja2ext.CompressorExtension'
    )
except KeyError:
    # happens if the urlconf is loaded twice
    pass
jingo.env.add_extension(CompressorExtension)


urlpatterns = patterns(
    '',
    (r'', include(urls)),
    (r'', include(supersearch_urls)),
    (r'^api/tokens/', include('crashstats.tokens.urls', namespace='tokens')),
    (r'^api/', include('crashstats.api.urls', namespace='api')),
    (r'^symbols/', include('crashstats.symbols.urls', namespace='symbols')),
    # if we ever use the Django admin we might want to change this URL
    (r'^admin/', include('crashstats.manage.urls', namespace='manage')),
    (r'', include('django_browserid.urls')),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
