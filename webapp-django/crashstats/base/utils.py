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


def get_signature_startup_stats(signature):
    startup_stats = {'crash_count': signature['count']}

    # Number of plugin crashes.
    startup_stats['plugin_count'] = 0
    sig_process = signature['facets']['process_type']
    for row in sig_process:
        if row['term'].lower() == 'plugin':
            startup_stats['plugin_count'] = row['count']

    # Number of hang crashes.
    startup_stats['hang_count'] = 0
    sig_hang = signature['facets']['hang_type']
    for row in sig_hang:
        # Hangs have weird values in the database: a value of 1 or -1
        # means it is a hang, a value of 0 or missing means it is not.
        if row['term'] in (1, -1):
            startup_stats['hang_count'] += row['count']

    # Number of crashes happening during startup. This is defined by
    # the client, as opposed to the next method which relies on
    # the uptime of the client.
    startup_stats['startup_count'] = sum(
        row['count'] for row in signature['facets']['startup_crash']
        if row['term'] in ('T', '1')
    )

    # Is a startup crash if more than half of the crashes are happening
    # in the first minute after launch.
    startup_stats['startup_crash'] = False
    sig_uptime = signature['facets']['histogram_uptime']
    for row in sig_uptime:
        # Aggregation buckets use the lowest value of the bucket as
        # term. So for everything between 0 and 60 excluded, the
        # term will be `0`.
        if row['term'] < 60:
            ratio = 1.0 * row['count'] / signature['count']
            startup_stats['startup_crash'] = ratio > 0.5

    return startup_stats
