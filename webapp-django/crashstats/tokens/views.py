from django import http
from django.contrib.auth.models import Permission
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import RequestSite
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction

from . import models
from . import forms


@login_required
@transaction.commit_on_success
def home(request):
    context = {}

    all_possible_permissions = (
        Permission.objects.filter(content_type__model='')
        .order_by('name')
    )
    possible_permissions = []
    for permission in all_possible_permissions:
        if request.user.has_perm('crashstats.' + permission.codename):
            possible_permissions.append(permission)

    if request.method == 'POST':
        form = forms.GenerateTokenForm(
            request.POST,
            possible_permissions=possible_permissions
        )
        if form.is_valid():
            for permission in form.cleaned_data['permissions']:
                perm_name = 'crashstats.%s' % permission.codename
                if not request.user.has_perm(perm_name):
                    return http.HttpResponseForbidden(
                        'You do not have this permission'
                    )
            token = models.Token.objects.create(
                user=request.user,
                notes=form.cleaned_data['notes']
            )
            for permission in form.cleaned_data['permissions']:
                token.permissions.add(permission)
            return redirect('tokens:home')

    else:
        if possible_permissions:
            form = forms.GenerateTokenForm(
                possible_permissions=possible_permissions
            )
        else:
            # This is surprisingly important!
            # If you *have* permissions, you can actually create a
            # token without selecting *any* permissions. The point of
            # that is to avoid the rate limiter.
            # If you don't have any permissions attached to your user
            # account means you haven't been hand curated by any
            # administrator and if that's the case you shouldn't be able
            # avoid the rate limiter.
            form = None

    context['form'] = form
    context['your_tokens'] = (
        models.Token.objects
        .filter(user=request.user)
        .order_by('-created')
    )
    context['absolute_base_url'] = (
        '%s://%s' % (
            request.is_secure() and 'https' or 'http',
            RequestSite(request).domain
        )
    )

    return render(request, 'tokens/home.html', context)


@login_required
@transaction.commit_on_success
def delete_token(request, pk):
    token = get_object_or_404(models.Token, pk=pk, user=request.user)
    token.delete()
    return redirect('tokens:home')
