# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django import http
from django.contrib.auth.models import Permission
from django.contrib.sites.requests import RequestSite
from django.db import transaction
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect

from crashstats.crashstats.decorators import login_required, track_view
from crashstats.tokens import forms
from crashstats.tokens import models


@login_required
@track_view
@transaction.atomic
def home(request):
    context = {}

    all_possible_permissions = Permission.objects.filter(
        content_type__model=""
    ).order_by("name")
    possible_permissions = []
    for permission in all_possible_permissions:
        if request.user.has_perm("crashstats." + permission.codename):
            possible_permissions.append(permission)

    if request.method == "POST":
        form = forms.GenerateTokenForm(
            request.POST, possible_permissions=possible_permissions
        )
        if form.is_valid():
            if "permissions" in form.cleaned_data:
                for permission in form.cleaned_data["permissions"]:
                    perm_name = "crashstats.%s" % permission.codename
                    if not request.user.has_perm(perm_name):
                        return http.HttpResponseForbidden(
                            "You do not have this permission"
                        )
            token = models.Token.objects.create(
                user=request.user, notes=form.cleaned_data["notes"]
            )
            if "permissions" in form.cleaned_data:
                for permission in form.cleaned_data["permissions"]:
                    token.permissions.add(permission)
            return redirect("tokens:home")

    else:
        form = forms.GenerateTokenForm(possible_permissions=possible_permissions)

    context["possible_permissions"] = possible_permissions

    context["form"] = form
    context["your_tokens"] = models.Token.objects.filter(user=request.user).order_by(
        "-created"
    )
    context["absolute_base_url"] = "%s://%s" % (
        request.is_secure() and "https" or "http",
        RequestSite(request).domain,
    )

    return render(request, "tokens/home.html", context)


@require_POST
@login_required
@track_view
@transaction.atomic
def delete_token(request, pk):
    token = get_object_or_404(models.Token, pk=pk, user=request.user)
    token.delete()
    return redirect("tokens:home")
