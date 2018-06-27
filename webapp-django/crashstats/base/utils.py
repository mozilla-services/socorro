import urllib

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from django.template import engines


def render_exception(exception):
    """When we need to render an exception as HTML.

    Often used to supply as the response body when there's a
    HttpResponseBadRequest.
    """
    template = engines['backend'].from_string(
        '<ul><li>{{ exception }}</li></ul>'
    )
    return template.render({'exception': exception})


def urlencode_obj(thing):
    """Return a URL encoded string, created from a regular dict or any object
    that has a `urlencode` method.

    This function ensures white spaces are encoded with '%20' and not '+'.
    """
    if hasattr(thing, 'urlencode'):
        res = thing.urlencode()
    else:
        res = urllib.urlencode(thing, True)
    return res.replace('+', '%20')


def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=None,
):
    """Opinionated wrapper that creates a requests session with a
    HTTPAdapter that sets up a Retry policy that includes connection
    retries.

    If you do the more naive retry by simply setting a number. E.g.::

        adapter = HTTPAdapter(max_retries=3)

    then it will raise immediately on any connection errors.
    Retrying on connection errors guards better on unpredictable networks.
    From http://docs.python-requests.org/en/master/api/?highlight=retries#requests.adapters.HTTPAdapter
    it says: "By default, Requests does not retry failed connections."

    The backoff_factor is documented here:
    https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#urllib3.util.retry.Retry
    A default of retries=3 and backoff_factor=0.3 means it will sleep like::

        [0.3, 0.6, 1.2]

    Optionally you can pass in a list of status codes that you consider
    worthy of retries (just like a ConnectionError). For example::

        session = requests_retry_session(status_forcelist=(500, 502))
        session.get(...)

    Now, if the server responds with one of these errors, the session
    will just try again.
    """  # noqa
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_signatures_stats(results, previous_range_results, platforms):
    signatures = results['facets']['signature']
    num_signatures = results['total']
    platform_codes = [x['code'] for x in platforms if x['code'] != 'unknown']

    signatures_stats = []
    for i, signature in enumerate(signatures):
        signatures_stats.append(SignatureStats(signature, i, num_signatures, platform_codes))

    if num_signatures > 0 and 'signature' in previous_range_results['facets']:
        previous_signatures = get_comparison_signatures(previous_range_results)
        for signature_stats in signatures_stats:
            previous_signature = previous_signatures.get(signature_stats.signature)
            if previous_signature:
                signature_stats.diff = previous_signature['percent'] - signature_stats.percent
                signature_stats.rank_diff = previous_signature['rank'] - signature_stats.rank
                signature_stats.previous_percent = previous_signature['percent']
            else:
                signature_stats.diff = 'new'
                signature_stats.rank_diff = 0
                signature_stats.previous_percent = 0

    return signatures_stats


class SignatureStats:
    def __init__(self, signature, rank, num_signatures, platform_codes):
        self.signature = signature['term']
        self.rank = rank
        self.percent = 100.0 * signature['count'] / num_signatures
        self.count = signature['count']
        self.platforms = get_num_crashes_per_platform(signature['facets']['platform'],
                                                      platform_codes)
        self.is_gc_count = get_num_crashes_in_garbage_collection(
            signature['facets']['is_garbage_collecting'])
        self.installs_count = (signature['facets']['cardinality_install_time']['value'])
        self.startup_stats = SignatureStartupStats(signature)


class SignatureStartupStats:
    def __init__(self, signature):
        self.count = signature['count']
        self.plugin_count = get_num_plugin_crashes(signature['facets']['process_type'])
        self.hang_count = get_num_hang_crashes(signature['facets']['hang_type'])
        self.startup_count = get_num_startup_crashes(signature['facets']['startup_crash'])
        self.startup_crash = get_is_startup_crash(signature['facets']['histogram_uptime'],
                                                  signature['count'])


def get_num_crashes_per_platform(platform_facet, platform_codes):
    num_crashes_per_platform = {}
    for platform in platform_codes:
        num_crashes_per_platform[platform + '_count'] = 0
    for platform in platform_facet:
        code = platform['term'][:3].lower()
        if code in platform_codes:
            num_crashes_per_platform[code + '_count'] = platform['count']
    return num_crashes_per_platform


def get_num_crashes_in_garbage_collection(is_garbage_collecting_facet):
    num_crashes_in_garbage_collection = 0
    for row in is_garbage_collecting_facet:
        if row['term'].lower() == 't':
            num_crashes_in_garbage_collection = row['count']
    return num_crashes_in_garbage_collection


def get_num_plugin_crashes(process_type_facet):
    num_plugin_crashes = 0
    for row in process_type_facet:
        if row['term'].lower() == 'plugin':
            num_plugin_crashes = row['count']
    return num_plugin_crashes


def get_num_hang_crashes(hang_type_facet):
    num_hang_crashes = 0
    for row in hang_type_facet:
        # Hangs have weird values in the database: a value of 1 or -1
        # means it is a hang, a value of 0 or missing means it is not.
        if row['term'] in (1, -1):
            num_hang_crashes += row['count']
    return num_hang_crashes


def get_num_startup_crashes(startup_crash_facet):
    return sum(
        row['count'] for row in startup_crash_facet
        if row['term'] in ('T', '1')
    )


def get_is_startup_crash(histogram_uptime_facet, crash_count):
    is_startup_crash = False
    for row in histogram_uptime_facet:
        # Aggregation buckets use the lowest value of the bucket as
        # term. So for everything between 0 and 60 excluded, the
        # term will be `0`.
        if row['term'] < 60:
            ratio = 1.0 * row['count'] / crash_count
            is_startup_crash = ratio > 0.5
    return is_startup_crash


def get_comparison_signatures(results):
    signatures = results['facets']['signature']
    num_signatures = results['total']
    comparison_signatures = {}
    for i, signature in enumerate(signatures):
        comparison_signatures[signature['term']] = {
            'count': signature['count'],
            'rank': i + 1,
            'percent': 100.0 * signature['count'] / num_signatures
        }
    return comparison_signatures
