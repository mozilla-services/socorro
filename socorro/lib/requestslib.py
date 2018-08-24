# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def session_with_retries(url):
    """Generates a requests session that supports retries on HTTP 429

    :arg url: url to use for requests

    :returns: a requests Session instance

    """
    base_url = urlparse.urlparse(url).netloc
    scheme = urlparse.urlparse(url).scheme

    retries = Retry(total=32, backoff_factor=1, status_forcelist=[429])

    s = requests.Session()

    # Set the User-Agent header so we can distinguish our stuff from other stuff
    s.headers.update({
        'User-Agent': 'socorro-requests/1.0'
    })
    s.mount(scheme + '://' + base_url, HTTPAdapter(max_retries=retries))

    return s
