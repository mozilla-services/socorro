# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from crashstats.manage import admin_site


handler404 = "crashstats.crashstats.views.handler404"
handler500 = "crashstats.crashstats.views.handler500"


urlpatterns = [
    path("", include("crashstats.crashstats.urls", namespace="crashstats")),
    path("", include("crashstats.monitoring.urls", namespace="monitoring")),
    path("search/", include("crashstats.supersearch.urls", namespace="supersearch")),
    path("signature/", include("crashstats.signature.urls", namespace="signature")),
    path(
        "topcrashers/",
        include("crashstats.topcrashers.urls", namespace="topcrashers"),
    ),
    path("sources/", include("crashstats.sources.urls", namespace="sources")),
    path("api/tokens/", include("crashstats.tokens.urls", namespace="tokens")),
    path("api/", include("crashstats.api.urls", namespace="api")),
    path("profile/", include("crashstats.profile.urls", namespace="profile")),
    path(
        "documentation/",
        include("crashstats.documentation.urls", namespace="documentation"),
    ),
    # Static pages in Django admin
    path("siteadmin/", include("crashstats.manage.admin_urls", namespace="siteadmin")),
    # Django-model backed pages in Django admin
    path("siteadmin/", admin_site.site.urls),
    path("oidc/", include("mozilla_django_oidc.urls")),
]

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
