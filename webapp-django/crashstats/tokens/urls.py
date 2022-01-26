# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import re_path

from crashstats.tokens import views


app_name = "tokens"
urlpatterns = [
    re_path(r"^$", views.home, name="home"),
    re_path(r"^delete/(?P<pk>\d+)/$", views.delete_token, name="delete_token"),
]
