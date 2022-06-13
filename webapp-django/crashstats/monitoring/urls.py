# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from crashstats.monitoring import views


app_name = "monitoring"
urlpatterns = [
    path("monitoring/cron/", views.cron_status, name="cron_status"),
    path("monitoring/", views.index, name="index"),
    path("__broken__", views.broken, name="broken"),
    # Dockerflow endpoints
    path("__heartbeat__", views.dockerflow_heartbeat, name="dockerflow_heartbeat"),
    path(
        "__lbheartbeat__",
        views.dockerflow_lbheartbeat,
        name="dockerflow_lbheartbeat",
    ),
    path("__version__", views.dockerflow_version, name="dockerflow_version"),
]
