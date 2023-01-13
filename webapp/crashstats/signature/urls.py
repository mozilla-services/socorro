# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from crashstats.signature import views


# NOTE(willkg): make sure to update settings.OIDC_EXEMPT_URLS with xhr urls
app_name = "signature"
urlpatterns = [
    path("reports/", views.signature_reports, name="signature_reports"),
    path("comments/", views.signature_comments, name="signature_comments"),
    path("correlations/", views.signature_correlations, name="signature_correlations"),
    path(
        "aggregation/<str:aggregation>/",
        views.signature_aggregation,
        name="signature_aggregation",
    ),
    path("graphs/<str:field>/", views.signature_graphs, name="signature_graphs"),
    path("summary/", views.signature_summary, name="signature_summary"),
    path("bugzilla/", views.signature_bugzilla, name="signature_bugzilla"),
    path("", views.signature_report, name="signature_report"),
]
