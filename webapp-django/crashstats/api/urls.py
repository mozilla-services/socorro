# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import re_path

from crashstats.api import views


app_name = "api"
urlpatterns = [
    re_path(r"^$", views.documentation, name="documentation"),
    re_path(r"^CrashVerify/$", views.CrashVerifyAPI.as_view(), name="crash_verify"),
    re_path(
        r"^CrashSignature/$", views.CrashSignatureAPI.as_view(), name="crash_signature"
    ),
    re_path(r"^(?P<model_name>\w+)/$", views.model_wrapper, name="model_wrapper"),
]
