# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os

import elasticsearch

from django import http
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.shortcuts import render
from django.utils import timezone

from crashstats.crashstats import utils
from crashstats.cron.models import Job as CronJob
from crashstats.supersearch.models import SuperSearch


def index(request):
    return render(request, 'monitoring/index.html')


@utils.json_view
def crontabber_status(request):
    """Returns the high-level status of crontabber jobs"""
    context = {
        'status': 'ALLGOOD'
    }

    last_runs = []
    broken = []
    for job in CronJob.objects.all():
        if job.last_run:
            last_runs.append(job.last_run)

        if job.error_count:
            broken.append(job.app_name)

    # Adjust status based on last_run
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

    # Adjust status based on broken jobs
    if broken:
        context['status'] = 'Broken'
        context['broken'] = broken

    return context


def dockerflow_version(requst):
    """Dockerflow __version__ endpoint.

    Returns contents of /app/version.json or {}.

    """
    path = os.path.join(settings.SOCORRO_ROOT, 'version.json')
    if os.path.exists(path):
        with open(path, 'r') as fp:
            data = fp.read()
    else:
        data = '{}'
    return http.HttpResponse(data, content_type='application/json')


@utils.json_view
def dockerflow_heartbeat(request):
    """Dockerflow endpoint that checks backing services for connectivity.

    Returns HTTP 200 if everything is ok or HTTP 500 on error.

    """
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


@utils.json_view
def dockerflow_lbheartbeat(request):
    """Dockerflow endpoint for load balancer checks."""
    return {'ok': True}


@utils.json_view
def healthcheck(request):
    """Deprecated healthcheck endpoint."""
    if not request.GET.get('elb') in ('1', 'true'):
        return dockerflow_heartbeat(request)
    return dockerflow_lbheartbeat(request)


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
