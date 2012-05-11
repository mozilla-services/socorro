import requests
import json

from requests.auth import HTTPBasicAuth

class SocorroMiddleware(object):
    def fetch(self, url):
        headers = {'Host': 'socorro-api-dev-internal'}
        resp = requests.get(url, auth=('dbrwaccess', 'rauYi4Ow'),
                            headers=headers)
        return json.loads(resp.content)

    def current_versions(self):
        url = 'http://localhost:8080/bpapi/current/versions/'
        return self.fetch(url)['currentversions']

    def adu_by_day(self):
        url = 'http://localhost:8080/bpapi/adu/byday/p/Firefox/v/13.0a1;14.0a2;13.0b2;12.0/rt/any/os/Windows;Mac;Linux/start/2012-05-03/end/2012-05-10'
        return self.fetch(url)

    def tcbs(self):
        url = 'http://localhost:8080/bpapi/crashes/signatures/product/Firefox/version/14.0a1/crash_type/browser/end_date/2012-05-10T11%3A00%3A00%2B0000/duration/168/limit/300/'
        return self.fetch(url)

    def search(self):
        url = 'http://localhost:8080/bpapi/search/signatures/products/Firefox/in/signature/search_mode/contains/to/2012-04-22%2011%3A09%3A37/from/2012-04-15%2011%3A09%3A37/report_type/any/report_process/any/result_number/100/'
        return self.fetch(url)

