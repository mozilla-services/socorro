# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json

import elasticsearch

from django import http
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.shortcuts import render
from django.utils import timezone

from crashstats import productlib
from crashstats.crashstats import utils
from crashstats.cron import MAX_ONGOING
from crashstats.cron.models import Job as CronJob
from crashstats.supersearch.models import SuperSearch
from socorro.lib.revision_data import get_version


def index(request):
    return render(request, "monitoring/index.html")


@utils.json_view
def cron_status(request):
    """Returns the high-level status of cron jobs."""
    context = {"status": "ALLGOOD"}

    last_runs = []
    broken = []
    for job in CronJob.objects.all():
        if job.last_run:
            last_runs.append(job.last_run)

        if job.error_count:
            broken.append(job.app_name)

    # Adjust status based on last_run
    if last_runs:
        ancient_times = timezone.now() - datetime.timedelta(minutes=MAX_ONGOING)
        most_recent_run = max(last_runs)
        if most_recent_run < ancient_times:
            context["status"] = "Stale"
            context["last_run"] = max(last_runs)
    else:
        # if it's never run, then it's definitely stale
        context["status"] = "Stale"

    # Adjust status based on broken jobs
    if broken:
        context["status"] = "Broken"
        context["broken"] = broken

    return context


def dockerflow_version(requst):
    """Dockerflow __version__ endpoint.

    Returns contents of /app/version.json or {}.

    """
    data = json.dumps(get_version() or {})
    return http.HttpResponse(data, content_type="application/json")


@utils.json_view
def dockerflow_heartbeat(request):
    """Dockerflow endpoint that checks backing services for connectivity.

    Returns HTTP 200 if everything is ok or HTTP 500 on error.

    """
    # Perform some really basic DB queries.
    # There will always be permissions created
    assert Permission.objects.all().count() > 0

    # We should also be able to set and get a cache value
    cache_key = "__healthcheck__"
    cache.set(cache_key, 1, 10)
    assert cache.get(cache_key)
    cache.delete(cache_key)

    # Do a really basic Elasticsearch query
    es = elasticsearch.Elasticsearch(
        hosts=settings.ELASTICSEARCH_URLS,
        timeout=30,
        connection_class=elasticsearch.connection.RequestsHttpConnection,
        verify_certs=True,
    )
    es.info()  # will raise an error if there's a problem with the cluster

    # Check SuperSearch paginated results
    assert_supersearch_no_errors()
    return {"ok": True}


@utils.json_view
def dockerflow_lbheartbeat(request):
    """Dockerflow endpoint for load balancer checks."""
    return {"ok": True}


def assert_supersearch_no_errors():
    """Make sure an uncached SuperSearch query doesn't have any errors"""
    supersearch = SuperSearch()
    # We don't want any caching this time
    supersearch.cache_seconds = 0
    results = supersearch.get(
        product=productlib.get_default_product().name,
        _results_number=1,
        _columns=["uuid"],
        _facets_size=1,
    )
    assert not results["errors"], results["errors"]
