# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from crashstats.monitoring import views


app_name = 'monitoring'
urlpatterns = [
    url(r'^$',
        views.index,
        name='index'),
    url(r'^crontabber/$',
        views.crontabber_status,
        name='crontabber_status'),
    url(r'^healthcheck/$',
        views.healthcheck,
        name='healthcheck'),
]
