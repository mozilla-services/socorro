# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import re_path

from crashstats.topcrashers import views


app_name = "topcrashers"
urlpatterns = [re_path(r"^$", views.topcrashers, name="topcrashers")]
