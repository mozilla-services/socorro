# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, re_path

from crashstats.manage import admin_site
from crashstats.crashstats.monkeypatches import patch


patch()

handler404 = "crashstats.crashstats.views.handler404"
handler500 = "crashstats.crashstats.views.handler500"


urlpatterns = [
    re_path(r"", include("crashstats.crashstats.urls", namespace="crashstats")),
    re_path(r"", include("crashstats.exploitability.urls", namespace="exploitability")),
    re_path(r"", include("crashstats.monitoring.urls", namespace="monitoring")),
    re_path(
        r"^search/", include("crashstats.supersearch.urls", namespace="supersearch")
    ),
    re_path(
        r"^signature/", include("crashstats.signature.urls", namespace="signature")
    ),
    re_path(
        r"^topcrashers/",
        include("crashstats.topcrashers.urls", namespace="topcrashers"),
    ),
    re_path(r"^sources/", include("crashstats.sources.urls", namespace="sources")),
    re_path(r"^api/tokens/", include("crashstats.tokens.urls", namespace="tokens")),
    re_path(r"^api/", include("crashstats.api.urls", namespace="api")),
    re_path(r"^profile/", include("crashstats.profile.urls", namespace="profile")),
    re_path(
        r"^documentation/",
        include("crashstats.documentation.urls", namespace="documentation"),
    ),
    # Static pages in Django admin
    re_path(
        r"^siteadmin/", include("crashstats.manage.admin_urls", namespace="siteadmin")
    ),
    # Django-model backed pages in Django admin
    re_path(r"^siteadmin/", admin_site.site.urls),
    re_path(r"^oidc/", include("mozilla_django_oidc.urls")),
]

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
