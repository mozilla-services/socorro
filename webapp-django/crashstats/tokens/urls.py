# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from crashstats.tokens import views


app_name = "tokens"
urlpatterns = [
    path("", views.home, name="home"),
    path("delete/<int:pk>/", views.delete_token, name="delete_token"),
]
