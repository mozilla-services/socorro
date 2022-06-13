# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from crashstats.api import views


app_name = "api"
urlpatterns = [
    path("", views.documentation, name="documentation"),
    path("CrashVerify/", views.CrashVerifyAPI.as_view(), name="crash_verify"),
    path("CrashSignature/", views.CrashSignatureAPI.as_view(), name="crash_signature"),
    path("<str:model_name>/", views.model_wrapper, name="model_wrapper"),
]
