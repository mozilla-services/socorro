# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.urls import re_path
from django.views.generic import RedirectView

from crashstats.crashstats import views


products = r"/products/(?P<product>\w+)"
versions = r"/versions/(?P<versions>[;\w\.()]+)"
version = r"/versions/(?P<version>[;\w\.()]+)"

perm_legacy_redirect = settings.PERMANENT_LEGACY_REDIRECTS


app_name = "crashstats"
urlpatterns = [
    re_path(r"^contribute\.json$", views.contribute_json, name="contribute_json"),
    re_path(r"^favicon\.ico$", views.favicon_ico, name="favicon_ico"),
    re_path(r"^robots\.txt$", views.robots_txt, name="robots_txt"),
    re_path(
        r"^report/index/(?P<crash_id>[\w-]+)$", views.report_index, name="report_index"
    ),
    re_path(r"^search/quick/$", views.quick_search, name="quick_search"),
    re_path(r"^buginfo/bug", views.buginfo, name="buginfo"),
    re_path(r"^login/$", views.login, name="login"),
    re_path(r"^about/throttling/$", views.about_throttling, name="about_throttling"),
    re_path(
        r"^home/product/(?P<product>\w+)$", views.product_home, name="product_home"
    ),
    # Home page
    re_path(r"^$", views.home, name="home"),
    # Redirect deceased Advanced Search URL to Super Search
    re_path(
        r"^query/$",
        RedirectView.as_view(url="/search/", query_string=True, permanent=True),
    ),
    # Redirect old independant pages to the unified Profile page.
    re_path(
        r"^your-crashes/$",
        RedirectView.as_view(url="/profile/", permanent=perm_legacy_redirect),
    ),
    re_path(
        r"^permissions/$",
        RedirectView.as_view(url="/profile/", permanent=perm_legacy_redirect),
    ),
]
