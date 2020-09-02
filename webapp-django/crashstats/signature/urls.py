# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from crashstats.signature import views


# NOTE(willkg): make sure to update settings.OIDC_EXEMPT_URLS with xhr urls
app_name = "signature"
urlpatterns = [
    url(r"^reports/$", views.signature_reports, name="signature_reports"),
    url(r"^comments/$", views.signature_comments, name="signature_comments"),
    url(
        r"^correlations/$", views.signature_correlations, name="signature_correlations"
    ),
    url(
        r"^aggregation/(?P<aggregation>\w+)/$",
        views.signature_aggregation,
        name="signature_aggregation",
    ),
    url(r"^graphs/(?P<field>\w+)/$", views.signature_graphs, name="signature_graphs"),
    url(r"^summary/$", views.signature_summary, name="signature_summary"),
    url(r"^bugzilla/$", views.signature_bugzilla, name="signature_bugzilla"),
    url(r"^$", views.signature_report, name="signature_report"),
]
