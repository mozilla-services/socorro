# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url
from django.shortcuts import redirect

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
    url(
        r"^protected_data_access/$",
        views.protected_data_access,
        name="protected_data_access",
    ),
    # NOTE(willkg): Need to keep this redirect because it's linked to in a lot of
    # places like agreements in Bugzilla.
    url(
        r"^memory_dump_access/$",
        lambda request: redirect("documentation:protected_data_access"),
    ),
    url(
        r"^products/$",
        lambda request: redirect(
            "https://socorro.readthedocs.io/en/latest/products.html"
        ),
    ),
    url(r"^$", views.home, name="home"),
]
