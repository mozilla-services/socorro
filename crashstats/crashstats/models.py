import requests
import json
import memcache
import hashlib
import base64

from requests.auth import HTTPBasicAuth
from  django.conf import settings

class SocorroCommon(object):
    def __init__(self):
        if settings.USE_MEMCACHED:
            self.memc = memcache.Client([settings.MEMCACHED_SERVER], debug=1)
  
    def fetch(self, url, headers=None):
        if headers == None:
            headers = {'Host': self.http_host}

        auth = ()

        if self.username and self.password:
            auth=(self.username, self.password)

        if settings.USE_MEMCACHED:
            # URL may be very long, so take MD5 sum
            m = hashlib.md5()
            m.update(url)
            # MD5 sums may contain control characters, so base64 encode
            key = base64.b64encode(m.digest())
            result = self.memc.get(key)
            if not result:
                resp = requests.get(url=url, auth=auth, headers=headers)
                result = json.loads(resp.content)
                self.memc.set(key, result, settings.MEMCACHED_EXPIRATION)
        else:
            resp = requests.get(url=url, auth=auth, headers=headers)
            result = json.loads(resp.content)
       
        return result


class SocorroMiddleware(SocorroCommon):
    def __init__(self):
        super(SocorroMiddleware, self).__init__()
        self.base_url = settings.MWARE_BASE_URL
        self.http_host = settings.MWARE_HTTP_HOST
        self.username = settings.MWARE_USERNAME
        self.password = settings.MWARE_PASSWORD
 
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

class BugzillaAPI(SocorroCommon):
    def __init__(self):
        super(BugzillaAPI, self).__init__()
        self.username = self.password = None
        self.base_url = 'https://api-dev.bugzilla.mozilla.org/0.9/'

    def buginfo(self, bugs, fields):
        params = {
            'base_url': self.base_url,
            'bugs': ','.join(bugs),
            'fields': ','.join(fields),
        }
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        url = '%(base_url)s/bug?id=%(bugs)s&include_fields=%(fields)s' % params
        return self.fetch(url, headers)

