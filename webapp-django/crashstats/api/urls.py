# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from crashstats.api import views


app_name = "api"
urlpatterns = [
    url(r"^$", views.documentation, name="documentation"),
    url(r"^CrashVerify/$", views.CrashVerifyAPI.as_view(), name="crash_verify"),
    url(
        r"^CrashSignature/$", views.CrashSignatureAPI.as_view(), name="crash_signature"
    ),
    url(r"^(?P<model_name>\w+)/$", views.model_wrapper, name="model_wrapper"),
]
