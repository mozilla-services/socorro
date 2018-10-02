import datetime

import elasticsearch

from django.shortcuts import render
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import Permission
from django.core.cache import cache

from crashstats.crashstats import utils
from crashstats.crashstats.models import CrontabberState
from crashstats.supersearch.models import SuperSearch


def index(request):
    return render(request, 'monitoring/index.html')


@utils.json_view
def crontabber_status(request):
    api = CrontabberState()

    # start by assuming the status is OK which means no jobs are broken
    context = {'status': 'ALLGOOD'}

    all_apps = api.get()['state']
    last_runs = [
        x['last_run'] for x in all_apps.values()
        if x['last_run']
    ]
    if last_runs:
        ancient_times = timezone.now() - datetime.timedelta(
            minutes=settings.CRONTABBER_STALE_MINUTES
        )
        most_recent_run = max(last_runs)
        if most_recent_run < ancient_times:
            context['status'] = 'Stale'
            context['last_run'] = max(last_runs)
    else:
        # if it's never run, then it's definitely stale
        context['status'] = 'Stale'

    broken = [
        name for name, state in all_apps.items()
        if state['error_count']
    ]
    blocked = [
        name for name, state in all_apps.items()
        if set(broken) & set(state['depends_on'])
    ]

    # This infinite loop recurses deeper and deeper into the structure
    # to find all jobs that are blocked. If we find that job X is blocked
    # by job Y in iteration 1, we need to do another iteration to see if
    # there are jobs that are blocked by job X (which was blocked by job Y)
    while True:
        also_blocked = [
            name for name, state in all_apps.items()
            if name not in blocked and set(blocked) & set(state['depends_on'])
        ]
        if not also_blocked:
            break
        blocked += also_blocked

    if broken:
        # let's change our mind
        context['status'] = 'Broken'
        context['broken'] = broken
        context['blocked'] = blocked
    return context


@utils.json_view
def healthcheck(request):
    if not request.GET.get('elb') in ('1', 'true'):
        # Perform some really basic DB queries.
        # There will always be permissions created
        assert Permission.objects.all().count() > 0

        # We should also be able to set and get a cache value
        cache_key = '__healthcheck__'
        cache.set(cache_key, 1, 10)
        assert cache.get(cache_key)
        cache.delete(cache_key)

        # Do a really basic Elasticsearch query
        es_settings = (
            settings.SOCORRO_IMPLEMENTATIONS_CONFIG
            ['resource']['elasticsearch']
        )
        es = elasticsearch.Elasticsearch(
            hosts=es_settings['elasticsearch_urls']
        )
        es.info()  # will raise an error if there's a problem with the cluster

        # Check SuperSearch paginated results
        assert_supersearch_no_errors()

    return {'ok': True}


def assert_supersearch_no_errors():
    """Make sure an uncached SuperSearch query doesn't have any errors"""
    supersearch = SuperSearch()
    # We don't want any caching this time
    supersearch.cache_seconds = 0
    results = supersearch.get(
        product=settings.DEFAULT_PRODUCT,
        _results_number=1,
        _columns=['uuid'],
        _facets_size=1,
    )
    assert not results['errors'], results['errors']
