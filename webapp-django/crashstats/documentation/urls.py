# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from crashstats.documentation import views


app_name = "documentation"
urlpatterns = [
    url(r"^supersearch/$", views.supersearch_home, name="supersearch_home"),
    url(
        r"^supersearch/examples/$",
        views.supersearch_examples,
        name="supersearch_examples",
    ),
    url(r"^supersearch/api/$", views.supersearch_api, name="supersearch_api"),
    url(r"^memory_dump_access/$", views.memory_dump_access, name="memory_dump_access"),
    url(r"^products/$", views.products, name="products"),
    url(r"^$", views.home, name="home"),
]
