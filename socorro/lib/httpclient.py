import httplib


class HttpClient(object):
    """
    Class for doing HTTP request to any server.
    Mainly used for ElasticSearch. Encapsulate python's httplib.

    """

    def __init__(self, host, port):
        """
        Default constructor
        """
        self.host = host
        self.port = port

    def __enter__(self):
        self.conn = httplib.HTTPConnection(self.host + ":" + self.port)

    def __exit__(self, type, value, traceback):
        self.conn.close()

    def _process_response(self):
        response = self.conn.getresponse()
        if response.status == 200:
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
        """
        Send a HTTP GET request to a URL and return the result.

        """
        self.conn.request("GET", url)
        return self._process_response()

    def post(self, url, data):
        """
        Send a HTTP POST request to a URL and return the result.

        """
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Accept": "text/json"
        }
        self.conn.request("POST", url, data, headers)
        return self._process_response()
