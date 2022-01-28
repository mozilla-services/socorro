# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.urls import re_path

from crashstats.monitoring import views


app_name = "monitoring"
urlpatterns = [
    re_path(r"^monitoring/$", views.index, name="index"),
    re_path(r"^monitoring/cron/$", views.cron_status, name="cron_status"),
    re_path(r"^__broken__$", views.broken, name="broken"),
    # Dockerflow endpoints
    re_path(
        r"^__heartbeat__$", views.dockerflow_heartbeat, name="dockerflow_heartbeat"
    ),
    re_path(
        r"^__lbheartbeat__$",
        views.dockerflow_lbheartbeat,
        name="dockerflow_lbheartbeat",
    ),
    re_path(r"^__version__$", views.dockerflow_version, name="dockerflow_version"),
]
