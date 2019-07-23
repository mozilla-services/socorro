# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from crashstats.supersearch import views


app_name = "supersearch"
urlpatterns = [
    url(r"^search/$", views.search, name="search"),
    url(r"^search/custom/$", views.search_custom, name="search_custom"),
    url(r"^search/results/$", views.search_results, name="search_results"),
    url(r"^search/query/$", views.search_query, name="search_query"),
    url(r"^search/fields/$", views.search_fields, name="search_fields"),
]
