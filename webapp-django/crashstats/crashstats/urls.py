# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.conf.urls import url
from django.views.generic import RedirectView

from crashstats.crashstats import views


products = r"/products/(?P<product>\w+)"
versions = r"/versions/(?P<versions>[;\w\.()]+)"
version = r"/versions/(?P<version>[;\w\.()]+)"

perm_legacy_redirect = settings.PERMANENT_LEGACY_REDIRECTS


app_name = "crashstats"
urlpatterns = [
    url(r"^contribute\.json$", views.contribute_json, name="contribute_json"),
    url(r"^favicon\.ico$", views.favicon_ico, name="favicon_ico"),
    url(r"^robots\.txt$", views.robots_txt, name="robots_txt"),
    url(
        r"^report/index/(?P<crash_id>[\w-]+)$", views.report_index, name="report_index"
    ),
    url(r"^search/quick/$", views.quick_search, name="quick_search"),
    url(r"^buginfo/bug", views.buginfo, name="buginfo"),
    url(r"^signup/$", views.signup, name="signup"),
    url(r"^login/$", views.login, name="login"),
    url(r"^about/throttling/$", views.about_throttling, name="about_throttling"),
    url(r"^home/product/(?P<product>\w+)$", views.product_home, name="product_home"),
    # Home page
    url(r"^$", views.home, name="home"),
    # Redirect deceased Advanced Search URL to Super Search
    url(
        r"^query/$",
        RedirectView.as_view(url="/search/", query_string=True, permanent=True),
    ),
    # Redirect old independant pages to the unified Profile page.
    url(
        r"^your-crashes/$",
        RedirectView.as_view(url="/profile/", permanent=perm_legacy_redirect),
    ),
    url(
        r"^permissions/$",
        RedirectView.as_view(url="/profile/", permanent=perm_legacy_redirect),
    ),
]
