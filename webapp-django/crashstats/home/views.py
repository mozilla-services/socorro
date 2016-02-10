from django import http
from django.shortcuts import render

from crashstats.crashstats.decorators import pass_default_context
from crashstats.crashstats import models
from . import forms


@pass_default_context
def home(request, product, default_context=None):
    context = default_context or {}

    form = forms.HomeForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    context['days'] = form.cleaned_data['days']
    context['versions'] = form.cleaned_data['version']

    if not context['versions']:
        context['versions'] = [
            x['version']
            for x in context['releases'][product]
            if x['featured']
        ]

    platforms_api = models.Platforms()
    platforms = platforms_api.get()
    context['platforms'] = [x['name'] for x in platforms if x.get('display')]

    return render(request, 'home/home.html', context)
