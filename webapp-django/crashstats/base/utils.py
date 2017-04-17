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


def requests_retry_session(retries=3, backoff_factor=0.3):
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
    """  # noqa
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
