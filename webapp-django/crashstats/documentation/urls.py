# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.shortcuts import redirect
from django.urls import re_path

from crashstats.documentation import views


app_name = "documentation"
urlpatterns = [
    re_path(r"^supersearch/$", views.supersearch_home, name="supersearch_home"),
    re_path(
        r"^supersearch/examples/$",
        views.supersearch_examples,
        name="supersearch_examples",
    ),
    re_path(r"^supersearch/api/$", views.supersearch_api, name="supersearch_api"),
    re_path(r"^signup/$", views.signup, name="signup"),
    re_path(
        r"^protected_data_access/$",
        views.protected_data_access,
        name="protected_data_access",
    ),
    # NOTE(willkg): Need to keep this redirect because it's linked to in a lot of
    # places like agreements in Bugzilla.
    re_path(
        r"^memory_dump_access/$",
        lambda request: redirect("documentation:protected_data_access"),
    ),
    re_path(
        r"^products/$",
        lambda request: redirect(
            "https://socorro.readthedocs.io/en/latest/products.html"
        ),
    ),
    re_path(r"^whatsnew/$", views.whatsnew, name="whatsnew"),
    re_path(r"^$", views.home, name="home"),
]
