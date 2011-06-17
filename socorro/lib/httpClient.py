import httplib, urllib

class HttpClient(object):

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

	def _processResponse(self):
		response = self.conn.getresponse()
		if response.status == 200:
			data = response.read()
		else:
			data = {
				"error":  {
					"code" : response.status,
					"reason" : response.reason,
					"data" : response.read()
				}
			}

		return data

	def get(self, url):
		"""
		Send a HTTP GET request to a URL and return the result.
		"""
		self.conn.request("GET", url)
		return self._processResponse()

	def post(self, url, data):
		"""
		Send a HTTP POST request to a URL and return the result.
		"""
		headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/json"}
		self.conn.request("POST", url, data, headers)
		return self._processResponse()
