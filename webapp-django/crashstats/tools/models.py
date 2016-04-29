import datetime

from django import http
from django.conf import settings

from crashstats.tools import forms
from crashstats.crashstats import models
from crashstats.supersearch.models import SuperSearch


class NewSignatures(models.SocorroMiddleware):

    API_WHITELIST = None

    possible_params = (
        ('start_date', datetime.date),
        ('end_date', datetime.date),
        ('not_after', datetime.date),
        ('product', list),
        ('version', list),
    )

    def get(self, **kwargs):
        form = forms.NewSignaturesForm(kwargs)

        if not form.is_valid():
            return http.JsonResponse({
                'errors': form.errors
            }, status=400)

        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        not_after = form.cleaned_data['not_after']
        product = form.cleaned_data['product'] or settings.DEFAULT_PRODUCT

        # Make default values for all dates parameters.
        if not end_date:
            end_date = (
                datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
            )

        if not start_date:
            start_date = end_date - datetime.timedelta(days=8)

        if not not_after:
            not_after = start_date - datetime.timedelta(days=14)

        api = SuperSearch()

        signatures_number = 100

        # First let's get a list of the top signatures that appeared during
        # the period we are interested in.
        params = {
            'product': product,
            'version': form.cleaned_data['version'],
            'date': [
                '>=' + start_date.isoformat(),
                '<' + end_date.isoformat(),
            ],
            '_facets': 'signature',
            '_facets_size': signatures_number,
            '_results_number': 0,
        }
        data = api.get(**params)

        signatures = []
        for signature in data['facets']['signature']:
            signatures.append(signature['term'])

        # Now we want to verify whether those signatures appeared or not during
        # some previous period of time.
        params['date'] = [
            '>=' + not_after.isoformat(),
            '<' + start_date.isoformat(),
        ]

        # Filter exactly the signatures that we have.
        params['signature'] = ['=' + x for x in signatures]

        data = api.get(**params)

        # If any of those signatures is in the results, it's that it did not
        # appear during the period of time we are interested in. Let's
        # remove it from the list of new signatures.
        for signature in data['facets']['signature']:
            if signature['term'] in signatures:
                signatures.remove(signature['term'])

        # All remaining signatures are "new" ones.
        return {
            'hits': signatures,
            'total': len(signatures)
        }
