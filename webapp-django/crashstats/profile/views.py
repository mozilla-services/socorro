# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.shortcuts import render
from django.contrib.auth.models import Permission

from crashstats.crashstats.decorators import pass_default_context, login_required


@pass_default_context
@login_required
def profile(request, default_context=None):
    context = default_context or {}
    context["permissions"] = Permission.objects.filter(content_type__model="").order_by(
        "name"
    )

    return render(request, "profile/profile.html", context)
