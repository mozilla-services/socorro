# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.urls import re_path

from crashstats.manage import admin


app_name = "manage"
urlpatterns = [
    re_path(
        "^analyze-model-fetches/$",
        admin.analyze_model_fetches,
        name="analyze_model_fetches",
    ),
    re_path("^crash-me-now/$", admin.crash_me_now, name="crash_me_now"),
    re_path("^sitestatus/$", admin.site_status, name="site_status"),
    re_path(
        "^supersearch-fields/missing/$",
        admin.supersearch_fields_missing,
        name="supersearch_fields_missing",
    ),
    re_path(
        "^supersearch-status/$",
        admin.supersearch_status,
        name="supersearch_status",
    ),
    re_path(
        "^protected-data-users/$",
        admin.protected_data_users,
        name="protected_data_users",
    ),
]
