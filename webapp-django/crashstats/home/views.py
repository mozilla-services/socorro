import functools

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.generic.base import RedirectView

from crashstats.crashstats.decorators import pass_default_context
from crashstats.crashstats.utils import build_default_context


def handle_missing_product(view):
    """Handle a 404 due to missing product

    We want a more user-friendly "missing product" page with instructions and
    other things.

    """
    @functools.wraps(view)
    def inner(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except Http404:
            context = build_default_context()
            context['product'] = kwargs.get('product', 'No product')
            return render(request, 'home/missing_product.html', context, status=404)
    return inner


@handle_missing_product
@pass_default_context
def product_home(request, product, default_context=None):
    context = default_context or {}

    # Figure out versions
    context['versions'] = [
        x['version']
        for x in context['active_versions'][product]
        if x['is_featured']
    ]
    # If there are no featured versions but there are active
    # versions, then fall back to use that instead.
    if not context['versions'] and context['active_versions'][product]:
        # But when we do that, we have to make a manual cut-off of
        # the number of versions to return. So make it max 4.
        context['versions'] = [
            x['version']
            for x in context['active_versions'][product]
        ][:settings.NUMBER_OF_FEATURED_VERSIONS]

    return render(request, 'home/product_home.html', context)


class LegacyHomeRedirectView(RedirectView):

    permanent = settings.PERMANENT_LEGACY_REDIRECTS
    query_string = False
    pattern_name = 'home:product_home'

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
