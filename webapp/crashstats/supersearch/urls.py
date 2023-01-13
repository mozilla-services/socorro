# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from crashstats.supersearch import views


# NOTE(willkg): make sure to update settings.OIDC_EXEMPT_URLS with xhr urls
app_name = "supersearch"
urlpatterns = [
    path("", views.search, name="search"),
    path("custom/", views.search_custom, name="search_custom"),
    path("results/", views.search_results, name="search_results"),
    path("query/", views.search_query, name="search_query"),
    path("fields/", views.search_fields, name="search_fields"),
]
