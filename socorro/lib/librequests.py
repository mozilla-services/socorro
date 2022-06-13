# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class HTTPAdapterWithTimeout(HTTPAdapter):
    """HTTPAdapter with a default timeout

    This allows you to set a default timeout when creating the adapter.
    It can be overridden here as well as when doing individual
    requests.

    :arg varies default_timeout: number of seconds before timing out

        This can be a float or a (connect timeout, read timeout) tuple
        of floats.

        Defaults to 5.0 seconds.

    """

    def __init__(self, *args, **kwargs):
        self._default_timeout = kwargs.pop("default_timeout", 5.0)
        super().__init__(*args, **kwargs)

    def send(self, *args, **kwargs):
        # If there's a timeout, use that. Otherwise, use the default.
        kwargs["timeout"] = kwargs.get("timeout") or self._default_timeout
        return super().send(*args, **kwargs)


def session_with_retries(
    total_retries=5,
    backoff_factor=0.1,
    status_forcelist=(429, 500),
    default_timeout=3.0,
):
    """Returns session that retries on HTTP 429 and 500 with default timeout

    :arg int total_retries: total number of times to retry

    :arg float backoff_factor: number of seconds to apply between attempts

        The sleep amount is calculated like this::

            sleep = backoff_factor * (2 ** (num_retries - 1))

        For example, backoff_factor 0.1 will back off :

        * 0.1
        * 0.2
        * 0.4
        * 0.8
        * 1.6 ...

    :arg tuple of HTTP codes status_forcelist: tuple of HTTP codes to
        retry on

    :arg varies default_timeout: number of seconds before timing out

        This can be a float or a (connect timeout, read timeout) tuple
        of floats.

    :returns: a requests Session instance

    """
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=list(status_forcelist),
    )

    session = requests.Session()

    # Set the User-Agent header so we can distinguish our stuff from other stuff
    session.headers.update({"User-Agent": "socorro-requests/1.0"})

    adapter = HTTPAdapterWithTimeout(
        max_retries=retries, default_timeout=default_timeout
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session
