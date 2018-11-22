from __future__ import absolute_import

import os

from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from django.views.static import serve

from crashstats.manage import admin_site
from crashstats.base.monkeypatches import patch


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
    url(r'', include('crashstats.crashstats.urls', namespace='crashstats')),
    url(r'', include('crashstats.supersearch.urls', namespace='supersearch')),
    url(r'', include('crashstats.exploitability.urls', namespace='exploitability')),
    url(r'', include('crashstats.graphics.urls', namespace='graphics')),
    url(r'^signature/', include('crashstats.signature.urls', namespace='signature')),
    url(r'^topcrashers/', include('crashstats.topcrashers.urls', namespace='topcrashers')),
    url(r'^sources/', include('crashstats.sources.urls', namespace='sources')),
    url(r'^monitoring/', include('crashstats.monitoring.urls', namespace='monitoring')),
    url(r'^api/tokens/', include('crashstats.tokens.urls', namespace='tokens')),
    url(r'^api/', include('crashstats.api.urls', namespace='api')),
    # redirect all symbols/ requests to Tecken
    url(r'^symbols/.*',
        RedirectView.as_view(url='https://symbols.mozilla.org/'),
        name='redirect-to-tecken'),
    url(r'^profile/', include('crashstats.profile.urls', namespace='profile')),
    url(r'^documentation/', include('crashstats.documentation.urls', namespace='documentation')),

    # Static pages in Django admin
    url(r'^siteadmin/', include('crashstats.manage.admin_urls', namespace='siteadmin')),
    # Django-model backed pages in Django admin
    url(r'^siteadmin/', include(admin_site.site.urls)),
    url(r'^oidc/', include('mozilla_django_oidc.urls')),
]

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
