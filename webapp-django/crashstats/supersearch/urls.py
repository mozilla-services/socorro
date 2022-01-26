# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import re_path

from crashstats.supersearch import views


# NOTE(willkg): make sure to update settings.OIDC_EXEMPT_URLS with xhr urls
app_name = "supersearch"
urlpatterns = [
    re_path(r"^$", views.search, name="search"),
    re_path(r"^custom/$", views.search_custom, name="search_custom"),
    re_path(r"^results/$", views.search_results, name="search_results"),
    re_path(r"^query/$", views.search_query, name="search_query"),
    re_path(r"^fields/$", views.search_fields, name="search_fields"),
]
