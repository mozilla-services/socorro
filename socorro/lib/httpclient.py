# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import httplib


class HttpClient(object):
    """Class for doing HTTP requests to any server. Encapsulate python's httplib.
    """

    def __init__(self, host, port, timeout=None):
        """Set the host, port and optional timeout for all HTTP requests ran by
        this client.
        """
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        self.conn = httplib.HTTPConnection(self.host, self.port,
                                           timeout=self.timeout)

    def __exit__(self, type, value, traceback):
        self.conn.close()

    def _process_response(self):
        """Return a JSON result after an HTTP Request.

        Process the response of an HTTP Request and make it a JSON error if
        it failed. Otherwise return the response's content.

        """
        response = self.conn.getresponse()
        if response.status == 200 or response.status == 201:
            data = response.read()
        else:
            data = {
                "error":  {
                    "code": response.status,
                    "reason": response.reason,
                    "data": response.read()
                }
            }

        return data

    def get(self, url):
        """Send a HTTP GET request to a URL and return the result.
        """
        self.conn.request("GET", url)
        return self._process_response()

    def post(self, url, data):
        """Send a HTTP POST request to a URL and return the result.
        """
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Accept": "text/json"
        }
        self.conn.request("POST", url, data, headers)
        return self._process_response()

    def put(self, url, data=None):
        """Send a HTTP PUT request to a URL and return the result.
        """
        self.conn.request("PUT", url, data)
        return self._process_response()

    def delete(self, url):
        """Send a HTTP DELETE request to a URL and return the result.
        """
        self.conn.request("DELETE", url)
        return self._process_response()
