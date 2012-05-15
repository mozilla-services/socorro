import requests
import json

from requests.auth import HTTPBasicAuth
from django.conf import settings

class SocorroMiddleware(object):
    def __init__(self):
        self.base_url = settings.MWARE_BASE_URL
        self.http_host = settings.MWARE_HTTP_HOST
        self.username = settings.MWARE_USERNAME
        self.password = settings.MWARE_PASSWORD
  
    def fetch(self, url):
        headers = {'Host': self.http_host}
        resp = requests.get(url, auth=(self.username, self.password),
                            headers=headers)
        print url
        print resp
        return json.loads(resp.content)

    def post(self, url, payload):
        headers = {'Host': self.http_host}
        resp = requests.post(url, auth=(self.username, self.password),
                            headers=headers, data=payload)
        print url
        print resp
        return json.loads(resp.content)

    def current_versions(self):
        url = '%s/current/versions/' % self.base_url
        return self.fetch(url)['currentversions']

    def adu_by_day(self, product, versions, os_names, start_date, end_date):
        params = {
            'base_url': self.base_url,
            'product': product,
            'versions': ';'.join(versions),
            'os_names': ';'.join(os_names),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
        }
        url = '%(base_url)s/adu/byday/p/%(product)s/v/%(versions)s/rt/any/os/%(os_names)s/start/%(start_date)s/end/%(end_date)s' % params
        return self.fetch(url)

    def tcbs(self, product, version, crash_type, end_date, duration,
             limit=300):
        params = {
            'base_url': self.base_url,
            'product': product,
            'version': version,
            'crash_type': crash_type,
            'end_date': end_date,
            'duration': duration,
            'limit': limit,
        }

        url = '%(base_url)s/crashes/signatures/product/%(product)s/version/%(version)s/crash_type/%(crash_type)s/end_date/%(end_date)s/duration/%(duration)s/limit/%(limit)s/' % params
        return self.fetch(url)

    def report_list(self, signature, product_versions, start_date,
                    result_number):
        params = {
            'base_url': self.base_url,
            'signature': signature,
            'product_versions': product_versions,
            'start_date': start_date,
            'result_number': result_number,
        }
        url = '%(base_url)s/report/list/signature/%(signature)s/versions/%(product_versions)s/fields/signature/search_mode/contains/from/%(start_date)s/report_type/any/report_process/any/result_number/%(result_number)s/' % params
        return self.fetch(url)

    def report_index(self, crash_id):
        params = {
            'base_url': self.base_url,
            'crash_id': crash_id,
        }
        url = '%(base_url)s/crash/processed/by/uuid/%(crash_id)s' % params
        return self.fetch(url)

    def search(self, product, versions, os_names, start_date, end_date,
               limit=100):
        params = {
            'base_url': self.base_url,
            'product': product,
            'versions': versions,
            'os_names': os_names,
            'start_date': start_date,
            'end_date': end_date,
            'limit': limit,
        }
        url = '%(base_url)s/search/signatures/products/%(product)s/in/signature/search_mode/contains/to/%(end_date)s/from/%(start_date)s/report_type/any/report_process/any/result_number/%(limit)s/' % params
        return self.fetch(url)

    def bugs(self, signatures):
        params = {
            'base_url': self.base_url,
            'signatures': signatures,
        }
        url = '%(base_url)s/bugs/by/signatures' % params
        payload = { 'id': signatures }
        return self.post(url, payload)

