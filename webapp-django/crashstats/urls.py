# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView

from crashstats.manage import admin_site
from crashstats.crashstats.monkeypatches import patch


patch()

handler404 = "crashstats.crashstats.views.handler404"
handler500 = "crashstats.crashstats.views.handler500"


urlpatterns = [
    url(r"", include("crashstats.crashstats.urls", namespace="crashstats")),
    url(r"", include("crashstats.exploitability.urls", namespace="exploitability")),
    url(r"", include("crashstats.monitoring.urls", namespace="monitoring")),
    url(r"^search/", include("crashstats.supersearch.urls", namespace="supersearch")),
    url(r"^signature/", include("crashstats.signature.urls", namespace="signature")),
    url(
        r"^topcrashers/",
        include("crashstats.topcrashers.urls", namespace="topcrashers"),
    ),
    url(r"^sources/", include("crashstats.sources.urls", namespace="sources")),
    url(r"^api/tokens/", include("crashstats.tokens.urls", namespace="tokens")),
    url(r"^api/", include("crashstats.api.urls", namespace="api")),
    # redirect all symbols/ requests to Tecken
    url(
        r"^symbols/.*",
        RedirectView.as_view(url="https://symbols.mozilla.org/"),
        name="redirect-to-tecken",
    ),
    url(r"^profile/", include("crashstats.profile.urls", namespace="profile")),
    url(
        r"^documentation/",
        include("crashstats.documentation.urls", namespace="documentation"),
    ),
    # Static pages in Django admin
    url(r"^siteadmin/", include("crashstats.manage.admin_urls", namespace="siteadmin")),
    # Django-model backed pages in Django admin
    url(r"^siteadmin/", admin_site.site.urls),
    url(r"^oidc/", include("mozilla_django_oidc.urls")),
]

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
