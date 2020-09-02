# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from crashstats.supersearch import views


# NOTE(willkg): make sure to update settings.OIDC_EXEMPT_URLS with xhr urls
app_name = "supersearch"
urlpatterns = [
    url(r"^$", views.search, name="search"),
    url(r"^custom/$", views.search_custom, name="search_custom"),
    url(r"^results/$", views.search_results, name="search_results"),
    url(r"^query/$", views.search_query, name="search_query"),
    url(r"^fields/$", views.search_fields, name="search_fields"),
]
