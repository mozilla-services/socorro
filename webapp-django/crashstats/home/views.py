from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.generic.base import RedirectView

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
            for x in context['active_versions'][product]
            if x['is_featured']
        ]

    # Set selected version for the navigation bar.
    if len(context['versions']) == 1:
        context['version'] = context['versions'][0]

    platforms_api = models.Platforms()
    platforms = platforms_api.get()
    context['platforms'] = [x['name'] for x in platforms if x.get('display')]

    context['es_shards_per_index'] = settings.ES_SHARDS_PER_INDEX

    return render(request, 'home/home.html', context)


class LegacyHomeRedirectView(RedirectView):

    permanent = settings.PERMANENT_LEGACY_REDIRECTS
    query_string = False
    pattern_name = 'home:home'

    def get_redirect_url(self, *args, **kwargs):
        versions = None
        if 'versions' in kwargs:
            versions = kwargs['versions'].split(';')
            del kwargs['versions']

        url = super(LegacyHomeRedirectView, self).get_redirect_url(
            *args, **kwargs
        )

        if versions:
            url = '{}?{}'.format(
                url,
                '&'.join('version={}'.format(x) for x in versions)
            )

        return url
