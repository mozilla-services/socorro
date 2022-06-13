# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.urls import path, register_converter
from django.views.generic import RedirectView

from crashstats.crashstats import views


products = r"/products/(?P<product>\w+)"
versions = r"/versions/(?P<versions>[;\w\.()]+)"
version = r"/versions/(?P<version>[;\w\.()]+)"

perm_legacy_redirect = settings.PERMANENT_LEGACY_REDIRECTS


class CrashID:
    regex = r"(bp-)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(CrashID, "crashid")


app_name = "crashstats"
urlpatterns = [
    path("contribute.json", views.contribute_json, name="contribute_json"),
    path("favicon.ico", views.favicon_ico, name="favicon_ico"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("report/index/<crashid:crash_id>", views.report_index, name="report_index"),
    path("search/quick/", views.quick_search, name="quick_search"),
    path("buginfo/bug", views.buginfo, name="buginfo"),
    path("login/", views.login, name="login"),
    path("about/throttling/", views.about_throttling, name="about_throttling"),
    path("home/product/<str:product>", views.product_home, name="product_home"),
    # Home page
    path("", views.home, name="home"),
    # Redirect deceased Advanced Search URL to Super Search
    path(
        "query/",
        RedirectView.as_view(url="/search/", query_string=True, permanent=True),
    ),
    # Redirect old independant pages to the unified Profile page.
    path(
        "your-crashes/",
        RedirectView.as_view(url="/profile/", permanent=perm_legacy_redirect),
    ),
    path(
        "permissions/",
        RedirectView.as_view(url="/profile/", permanent=perm_legacy_redirect),
    ),
]
