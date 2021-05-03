# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from crashstats.manage import admin


app_name = "manage"
urlpatterns = [
    url(
        "^analyze-model-fetches/$",
        admin.analyze_model_fetches,
        name="analyze_model_fetches",
    ),
    url("^crash-me-now/$", admin.crash_me_now, name="crash_me_now"),
    url("^sitestatus/$", admin.site_status, name="site_status"),
    url(
        "^supersearch-fields/missing/$",
        admin.supersearch_fields_missing,
        name="supersearch_fields_missing",
    ),
    url(
        "^supersearch-status/$",
        admin.supersearch_status,
        name="supersearch_status",
    ),
    url(
        "^protected-data-users/$",
        admin.protected_data_users,
        name="protected_data_users",
    ),
]
