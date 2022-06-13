# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.shortcuts import redirect
from django.urls import path

from crashstats.documentation import views


app_name = "documentation"
urlpatterns = [
    path("supersearch/", views.supersearch_home, name="supersearch_home"),
    path(
        "supersearch/examples/",
        views.supersearch_examples,
        name="supersearch_examples",
    ),
    path("supersearch/api/", views.supersearch_api, name="supersearch_api"),
    path("signup/", views.signup, name="signup"),
    path(
        "protected_data_access/",
        views.protected_data_access,
        name="protected_data_access",
    ),
    # NOTE(willkg): Need to keep this redirect because it's linked to in a lot of
    # places like agreements in Bugzilla.
    path(
        "memory_dump_access/",
        lambda request: redirect("documentation:protected_data_access"),
    ),
    path(
        "products/",
        lambda request: redirect(
            "https://socorro.readthedocs.io/en/latest/products.html"
        ),
    ),
    path("whatsnew/", views.whatsnew, name="whatsnew"),
    path("", views.home, name="home"),
]
