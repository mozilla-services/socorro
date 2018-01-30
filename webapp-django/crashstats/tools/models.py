import datetime

from django import http
from django.conf import settings

from crashstats.tools import forms
from crashstats.crashstats import models
from crashstats.supersearch.models import SuperSearch
from elasticsearch.exceptions import NotFoundError, RequestError
from elasticsearch_dsl import Q, Search
from socorro.external.es import supersearch


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


class CrashStopDataImpl(supersearch.SuperSearch):

    def __init__(self, *args, **kwargs):
        super(CrashStopDataImpl, self).__init__(*args, **kwargs)

    def get_indices_from_buildids(self, buildids):
        dates = map(lambda bid: datetime.datetime.strptime(bid, '%Y%m%d%H%M%S'), buildids)
        start_date = min(dates)
        end_date = datetime.datetime.utcnow()

        return self.get_list_of_indices(start_date, end_date)

    def get(self, **kwargs):
        signatures = kwargs.get('signature')
        buildids = kwargs.get('buildid')
        products = kwargs.get('product')
        channels = kwargs.get('channel')

        # Find the indices to use to optimize the elasticsearch query.
        indices = set(self.get_indices_from_buildids(buildids))
        all_indices = self.es_context.indices_client().get_aliases().keys()
        indices = list(indices & set(all_indices))

        # Create and configure the search object.
        search = Search(
            using=self.get_connection(),
            index=indices,
            doc_type=self.config.elasticsearch.elasticsearch_doctype,
        )

        # Create the search query
        # First, the filters
        queries = []
        queries.append(Q('terms', **{'processed_crash.signature.full': signatures}))
        queries.append(Q('terms', **{'processed_crash.build': buildids}))
        queries.append(Q('terms', **{'processed_crash.product.full': products}))
        queries.append(Q('terms', **{'processed_crash.release_channel': channels}))
        search = search.query(Q('bool', must=queries))
        search = search.extra(size=0)

        # Second, the aggregations
        search.aggs.bucket('signature',
                           'terms',
                           field='processed_crash.signature.full',
                           size=len(signatures))\
                   .bucket('product',
                           'terms',
                           field='processed_crash.product.full')\
                   .bucket('release_channel',
                           'terms',
                           field='processed_crash.release_channel')\
                   .bucket('version',
                           'terms',
                           field='processed_crash.version',
                           size=50)\
                   .bucket('build_id',
                           'terms',
                           field='processed_crash.build',
                           size=len(buildids))\
                   .metric('count_install_time',
                           'value_count',
                           field='raw_crash.InstallTime')\
                   .bucket('startup_crashes',
                           'filter',
                           range={'processed_crash.uptime': {'gte': 0, 'lt': 60}})\
                   .metric('count_startup_crashes',
                           'value_count',
                           field='processed_crash.uptime')
        try:
            results = search.execute()
        except (NotFoundError, RequestError) as e:
            return {'errors': str(e)}

        aggregations = getattr(results, 'aggregations', {})
        aggregations = self.format_aggregations(aggregations)

        return aggregations


class CrashStopData(models.SocorroMiddleware):
    """
    Get crash data by (product, release_channel, version, build_id) for a set of signatures.
    """

    implementation_config_namespace = 'elasticsearch'
    implementation = CrashStopDataImpl

    API_WHITELIST = None

    required_params = (
        ('buildid', list),
        ('signature', list),
        ('product', list),
        ('channel', list)
    )
