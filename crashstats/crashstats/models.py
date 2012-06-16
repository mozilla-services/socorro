import os
import urlparse
import json
import logging
import requests

from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import iri_to_uri
from django.utils.hashcompat import md5_constructor
from django.template.defaultfilters import slugify


class BadStatusCodeError(Exception):  # XXX poor name
    pass


def _clean_path(path):
    """return a cleaned up version of the path appropriate for saving
    as a file directory.
    """
    path = iri_to_uri(path)
    path = path.replace(' ', '_')
    path = '/'.join(slugify(x) for x in path.split('/'))
    if path.startswith('/'):
        path = path[1:]
    return path


def _clean_query(query):
    return _clean_path(query.replace('&', '/'))


class SocorroCommon(object):

    # by default, we don't need username and password
    username = password = None
    # http_host
    http_host = None

    # default cache expiration time if applicable
    cache_seconds = 60 * 60

    def fetch(self, url, headers=None, method='get', data=None):
        if url.startswith('/'):
            url = self._complete_url(url)

        if not headers:
            if self.http_host:
                headers = {'Host': self.http_host}
            else:
                headers = {}

        if self.username and self.password:
            auth = self.username, self.password
        else:
            auth = ()

        cache_key = None
        cache_file = None
        if settings.CACHE_MIDDLEWARE_FILES:
            root = settings.CACHE_MIDDLEWARE_FILES
            if not isinstance(root, basestring):
                # e.g. it's a boolean
                cache_file = os.path.join(settings.ROOT, 'models-cache')
                split = urlparse.urlparse(url)
                cache_file = os.path.join(cache_file,
                                          split.netloc,
                                          _clean_path(split.path))
                if split.query:
                    cache_file = os.path.join(cache_file,
                                              _clean_query(split.query))

                cache_file = os.path.join(cache_file,
                      '%s.json' % md5_constructor(iri_to_uri(url)).hexdigest())

                if os.path.isfile(cache_file):
                    logging.debug("CACHE FILE HIT %s" % url)
                    return json.load(open(cache_file))

        if settings.CACHE_MIDDLEWARE:
            cache_key = md5_constructor(iri_to_uri(url)).hexdigest()
            result = cache.get(cache_key)
            if result is not None:
                logging.debug("CACHE HIT %s" % url)
                return result

        if method == 'post':
            request_method = requests.post
        elif method == 'get':
            request_method = requests.get
        else:
            raise ValueError(method)
        logging.info("FETCHING %s" % url)
        resp = request_method(url=url, auth=auth, headers=headers, data=data)
        if not resp.status_code == 200:
            raise BadStatusCodeError('%s: on: %s' % (resp.status_code, url))

        result = json.loads(resp.content)

        if cache_key:
            cache.set(cache_key, result, self.cache_seconds)
            if cache_file:
                if not os.path.isdir(os.path.dirname(cache_file)):
                    os.makedirs(os.path.dirname(cache_file))
                json.dump(result, open(cache_file, 'w'), indent=2)

        return result

    def _complete_url(self, url):
        if url.startswith('/'):
            if not getattr(self, 'base_url', None):
                raise NotImplementedError("No base_url defined in context")
            url = '%s%s' % (self.base_url, url)
        return url


class SocorroMiddleware(SocorroCommon):

    base_url = settings.MWARE_BASE_URL
    http_host = settings.MWARE_HTTP_HOST
    username = settings.MWARE_USERNAME
    password = settings.MWARE_PASSWORD

#    def fetch(self, url, *args, **kwargs):
#        url = self._complete_url(url)
#        return super(SocorroMiddleware, self).fetch(url, *args, **kwargs)

    def post(self, url, payload):
        url = self._complete_url(url)
        headers = {'Host': self.http_host}
        return self.fetch(url, headers=headers, method='post', data=payload)


class CurrentVersions(SocorroMiddleware):

    def get(self):
        url = '%s/current/versions/' % self.base_url
        return self.fetch(url)['currentversions']


class ADUByDay(SocorroMiddleware):

    def get(self, product, versions, os_names, start_date, end_date):
        params = {
            'product': product,
            'versions': ';'.join(versions),
            'os_names': ';'.join(os_names),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
        }
        url = ('/adu/byday/p/%(product)s/v/%(versions)s/rt/any/os/'
               '%(os_names)s/start/%(start_date)s/end/%(end_date)s' % params)
        return self.fetch(url)


class TCBS(SocorroMiddleware):

    def get(self, product, version, crash_type, end_date, duration,
             limit=300):
        params = {
            'product': product,
            'version': version,
            'crash_type': crash_type,
            'end_date': end_date,
            'duration': duration,
            'limit': limit,
        }
        url = ('/crashes/signatures/product/%(product)s/version/'
               '%(version)s/crash_type/%(crash_type)s/end_date/%(end_date)s/'
               'duration/%(duration)s/limit/%(limit)s/' % params)
        return self.fetch(url)


class ReportList(SocorroMiddleware):

    def get(self, signature, product_versions, start_date, result_number):
        params = {
            'signature': signature,
            'product_versions': product_versions,
            'start_date': start_date,
            'result_number': result_number,
        }

        url = ('/report/list/signature/%(signature)s/versions/'
               '%(product_versions)s/fields/signature/search_mode/contains/'
               'from/%(start_date)s/report_type/any/report_process/any/'
               'result_number/%(result_number)s/' % params)
        return self.fetch(url)


class ReportIndex(SocorroMiddleware):

    def get(self, crash_id):
        params = {
            'crash_id': crash_id,
        }
        url = '/crash/processed/by/uuid/%(crash_id)s' % params
        return self.fetch(url)

class CommentsBySignature(SocorroMiddleware):

    def get(self, signature, start_date, end_date, report_type='any',
            report_process='any'):
        params = {
            'signature': signature,
            'start_date': start_date,
            'end_date': end_date,
            'report_type': report_type, 
            'report_process': report_process
        }
        url = '/crashes/comments/signature/%(signature)s/search_mode/contains/to/%(end_date)s/from/%(start_date)s/report_type/%(report_type)s/report_process/%(report_process)s/' % params
        return self.fetch(url)


class Search(SocorroMiddleware):

    def get(self, product, versions, os_names, start_date, end_date,
               limit=100):
        params = {
            'product': product,
            'versions': versions,
            'os_names': os_names,
            'start_date': start_date,
            'end_date': end_date,
            'limit': limit,
        }
        url = ('/search/signatures/products/%(product)s/in/signature/'
               'search_mode/contains/to/%(end_date)s/from/%(start_date)s/'
               'report_type/any/report_process/any/result_number/%(limit)s/'
               % params)
        return self.fetch(url)


class Bugs(SocorroMiddleware):

    def get(self, signatures):
        url = '/bugs/by/signatures'
        payload = {'id': signatures}
        return self.post(url, payload)


class SignatureTrend(SocorroMiddleware):

    def get(self, product, version, signature, end_date, duration, steps=60):
        params = {
            'product': product,
            'version': version,
            'signature': signature,
            'end_date': end_date.strftime('%Y-%m-%d'),
            'duration': int(duration),
            'steps': steps,
        }
        url = ('/topcrash/sig/trend/history/p/%(product)s/v/%(version)s/sig/'
               '%(signature)s/end/%(end_date)s/duration/%(duration)s/steps/'
               '%(steps)s' % params)
        return self.fetch(url)


class SignatureSummary(SocorroMiddleware):

    def get(self, report_type, signature, start_date, end_date):
        params = {
            'report_type': report_type,
            'signature': signature,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
        }
        url = ('/signaturesummary/report_type/%(report_type)s/signature/'
               '%(signature)s/start_date/%(start_date)s/end_date/'
               '%(end_date)s' % params)
        return self.fetch(url)


class BugzillaAPI(SocorroCommon):
    base_url = 'https://api-dev.bugzilla.mozilla.org/0.9'
    username = password = None

#    def get(self, *args, **kwargs):
#        raise NotImplementedError("You're supposed to override this")


class BugzillaBugInfo(BugzillaAPI):

    def get(self, bugs, fields):
        if isinstance(bugs, basestring):
            bugs = [bugs]
        if isinstance(fields, basestring):
            fields = [fields]
        params = {
            'bugs': ','.join(bugs),
            'fields': ','.join(fields),
        }
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        url = ('/bug?id=%(bugs)s&include_fields=%(fields)s' % params)
        return self.fetch(url, headers)
