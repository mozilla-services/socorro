# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url
from django.views.generic import RedirectView

from crashstats.monitoring import views


app_name = "monitoring"
urlpatterns = [
    url(r"^monitoring/$", views.index, name="index"),
    url(r"^monitoring/cron/$", views.cron_status, name="cron_status"),
    # FIXME(willkg): Deprecated as of 4/30/2019
    url(
        r"^monitoring/crontabber/$",
        RedirectView.as_view(url="/monitoring/cron/", permanent=True),
    ),
    # Dockerflow endpoints
    url(r"^__heartbeat__$", views.dockerflow_heartbeat, name="dockerflow_heartbeat"),
    url(
        r"^__lbheartbeat__$",
        views.dockerflow_lbheartbeat,
        name="dockerflow_lbheartbeat",
    ),
    url(r"^__version__$", views.dockerflow_version, name="dockerflow_version"),
    # FIXME(willkg): DEPRECATED
    url(r"^monitoring/healthcheck/$", views.healthcheck, name="healthcheck"),
]
