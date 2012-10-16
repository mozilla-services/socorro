import datetime
import os
import urlparse
import json
import logging
import requests
import stat
import time
import urllib

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

    def fetch(self, url, headers=None, method='get', data=None,
              expect_json=True):
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

        if settings.CACHE_MIDDLEWARE:
            cache_key = md5_constructor(iri_to_uri(url)).hexdigest()
            result = cache.get(cache_key)
            if result is not None:
                logging.debug("CACHE HIT %s" % url)
                return result

            # not in the memcache/locmem but is it in cache files?

            if settings.CACHE_MIDDLEWARE_FILES:
                root = settings.CACHE_MIDDLEWARE_FILES
                if isinstance(root, bool):
                    cache_file = os.path.join(settings.ROOT, 'models-cache')
                else:
                    cache_file = root
                split = urlparse.urlparse(url)
                cache_file = os.path.join(cache_file,
                                          split.netloc,
                                          _clean_path(split.path))
                if split.query:
                    cache_file = os.path.join(cache_file,
                                              _clean_query(split.query))

                if expect_json:
                    cache_file = os.path.join(cache_file,
                                              '%s.json' % cache_key)
                else:
                    cache_file = os.path.join(cache_file,
                                              '%s.dump' % cache_key)

                if os.path.isfile(cache_file):
                    # but is it fresh enough?
                    age = time.time() - os.stat(cache_file)[stat.ST_MTIME]
                    if age > self.cache_seconds:
                        logging.debug("CACHE FILE TOO OLD")
                        os.remove(cache_file)
                    else:
                        logging.debug("CACHE FILE HIT %s" % url)
                        if expect_json:
                            return json.load(open(cache_file))
                        else:
                            return open(cache_file).read()

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

        result = resp.content
        if expect_json:
            result = json.loads(result)

        if cache_key:
            cache.set(cache_key, result, self.cache_seconds)
            if cache_file:
                if not os.path.isdir(os.path.dirname(cache_file)):
                    os.makedirs(os.path.dirname(cache_file))
                if expect_json:
                    json.dump(result, open(cache_file, 'w'), indent=2)
                else:
                    open(cache_file, 'w').write(result)

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

    default_date_format = '%Y-%m-%d'
    default_datetime_format = '%Y-%m-%dT%H:%M:%S'

#    def fetch(self, url, *args, **kwargs):
#        url = self._complete_url(url)
#        return super(SocorroMiddleware, self).fetch(url, *args, **kwargs)

    def post(self, url, payload):
        url = self._complete_url(url)
        headers = {'Host': self.http_host}
        return self.fetch(url, headers=headers, method='post', data=payload)

    def urlencode_params(self, params):
        """in-place replacement URL encoding parameter values.
        For example, if params == {'foo': 'bar1 bar2'}
        it changes it to == {'foo': 'bar1%20bar2'}
        """
        for key, value in params.iteritems():
            if isinstance(value, datetime.datetime):
                value = value.strftime(self.default_datetime_format)
            if isinstance(value, datetime.date):
                value = value.strftime(self.default_date_format)
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            if isinstance(value, basestring):
                params[key] = urllib.quote(value).replace('/', '%2F')


class CurrentVersions(SocorroMiddleware):

    def get(self):
        url = '%s/current/versions/' % self.base_url
        return self.fetch(url)['currentversions']


class CurrentProducts(SocorroMiddleware):

    def get(self, versions=None):
        url = '/products/'
        if versions:
            params = {
                'versions': versions
            }
            self.urlencode_params(params)
            url += 'versions/%(versions)s' % params

        return self.fetch(url)


class ProductsVersions(CurrentVersions):

    def get(self):
        versions = super(ProductsVersions, self).get()
        products = {}
        for version in versions:
            product = version['product']
            if product not in products:
                products[product] = []
            products[product].append(version)
        return products


class Platforms(SocorroMiddleware):

    def get(self):
        # For dev only, this should be moved to a middleware service
        # using the database as soon as possible.
        platforms = [
            {
                'code': 'windows',
                'name': 'Windows'
            },
            {
                'code': 'mac',
                'name': 'Mac OS X'
            },
            {
                'code': 'linux',
                'name': 'Linux'
            }
        ]
        return platforms


class CrashesPerAdu(SocorroMiddleware):

    # Fetch records for active daily users.
    def get(self, **kwargs):
        possible_params = [
            'product',
            'versions',
            'from_date',
            'to_date',
            'date_range_type',
            'os',
            'report_type'
        ]
        url = '/crashes/daily'
        params = {}

        for param in possible_params:
            if param not in kwargs:
                continue

            if param is 'os':
                # Operating systems can be specified for by version as
                # well but, we only want to separate the results by OS
                # if the selected, report type was by_os.
                if ('form_selection' in kwargs and
                    kwargs.get('form_selection') == 'by_os'):
                    params['separated_by'] = 'os'
                    url += '/separated_by/%(separated_by)s'

            value = kwargs[param]
            if isinstance(value, (list, tuple)):
                value = '+'.join(value)

            params[param] = value
            url += '/' + param + '/%(' + param + ')s'

        self.urlencode_params(params)

        return self.fetch(url % params)


class TCBS(SocorroMiddleware):

    def get(self, product, version, crash_type, end_date,
            date_range_type, duration, limit=300):
        params = {
            'product': product,
            'version': version,
            'crash_type': crash_type,
            'end_date': end_date.strftime('%Y-%m-%d'),
            'date_range_type': date_range_type,
            'duration': duration,
            'limit': limit
        }
        self.urlencode_params(params)

        url = ('/crashes/signatures/product/%(product)s/version/'
               '%(version)s/crash_type/%(crash_type)s/end_date/%(end_date)s/'
               'duration/%(duration)s/limit/%(limit)s/date_range_type/'
               '%(date_range_type)s/' % params)
        return self.fetch(url)


class ReportList(SocorroMiddleware):

    def get(self, signature, product_versions, start_date, result_number,
            result_offset):
        params = {
            'signature': signature,
            'product_versions': product_versions,
            'start_date': start_date,
            'result_number': result_number,
            'result_offset': result_offset,
        }
        self.urlencode_params(params)

        url = ('/report/list/signature/%(signature)s/versions/'
               '%(product_versions)s/fields/signature/search_mode/contains/'
               'from/%(start_date)s/report_type/any/report_process/any/'
               'result_number/%(result_number)s/'
               'result_offset/%(result_offset)s' % params)
        return self.fetch(url)


class ProcessedCrash(SocorroMiddleware):

    def get(self, crash_id):
        params = {
            'crash_id': crash_id,
        }
        self.urlencode_params(params)
        url = '/crash/processed/by/uuid/%(crash_id)s' % params
        return self.fetch(url)


class RawCrash(SocorroMiddleware):

    def get(self, crash_id, format='meta'):
        params = {
            'crash_id': crash_id,
            'format': format,
        }
        self.urlencode_params(params)
        url = '/crash/%(format)s/by/uuid/%(crash_id)s' % params
        return self.fetch(url, expect_json=format != 'raw_crash')


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
        self.urlencode_params(params)
        url = ('/crashes/comments/signature/%(signature)s/search_mode/'
               'contains/to/%(end_date)s/from/%(start_date)s/report_type/'
               '%(report_type)s/report_process/%(report_process)s/' % params)
        return self.fetch(url)


class CrashPairsByCrashId(SocorroMiddleware):

    def get(self, crash_id, hang_id):
        params = {
            'crash_id': crash_id,
            'hang_id': hang_id
        }
        self.urlencode_params(params)
        url = ('/crashes/paireduuid/uuid/%(crash_id)s/hangid/%(hang_id)s'
               % params)
        return self.fetch(url)


class HangReport(SocorroMiddleware):

    def get(self, product, version, end_date, duration, listsize, page):
        params = {
            'base_url': self.base_url,
            'product': product,
            'version': version,
            'end_date': end_date,
            'duration': duration,
            'listsize': listsize,
            'page': page
        }
        self.urlencode_params(params)
        url = ('/reports/hang/p/%(product)s/v/%(version)s/end/%(end_date)s/'
               'duration/%(duration)s/listsize/%(listsize)s/page/%(page)s'
               % params)
        return self.fetch(url)


class Search(SocorroMiddleware):

    def get(self, **kwargs):
        parameters = [
            'terms',
            'products',
            'versions',
            'os',
            'start_date',
            'end_date',
            'search_mode',
            'build_ids',
            'reasons',
            'report_process',
            'report_type',
            'plugin_in',
            'plugin_search_mode',
            'plugin_terms',
            'result_number',
            'result_offset'
        ]
        # This binding is here so we can easily remove it when the middleware
        # service is updated. That will happen when we have switched to
        # socorro-crashstats completely.
        params_binding = {
            'terms': 'for',
            'start_date': 'from',
            'end_date': 'to'
        }
        params_separator = '/'
        values_separator = '+'

        url_params = ['/search/signatures']
        for param in parameters:
            if param not in kwargs:
                continue

            value = kwargs.get(param)
            try:
                # For empty strings and lists
                valid = len(value) > 0
            except TypeError:
                # value was neither a string nor a list, it's valid by default
                valid = True

            if value is not None and valid:
                if param in params_binding:
                    param = params_binding[param]
                if isinstance(value, (list, tuple)):
                    value = values_separator.join(value)
                elif isinstance(value, unicode):
                    value = value.encode('utf-8')
                else:
                    value = str(value)
                url_params += [param, value]

        url_params.append('')  # trick to have the closing slash in url
        url = params_separator.join(url_params)

        return self.fetch(url)


class Bugs(SocorroMiddleware):

    def get(self, signatures):
        url = '/bugs/'
        payload = {'signatures': signatures}
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
        self.urlencode_params(params)
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
        self.urlencode_params(params)
        url = ('/signaturesummary/report_type/%(report_type)s/signature/'
               '%(signature)s/start_date/%(start_date)s/end_date/'
               '%(end_date)s' % params)
        return self.fetch(url)


class Status(SocorroMiddleware):

    def get(self, duration=12):
        return self.fetch('/server_status/duration/%s' % duration)


class DailyBuilds(SocorroMiddleware):

    def get(self, product, version=None):
        params = {
            'product': product
        }
        if version:
            params['version'] = version
            url = ('/products/builds/product/%(product)s/version/%(version)s'
                   % params)
        else:
            url = ('/products/builds/product/%(product)s' % params)
        return self.fetch(url)


class CrashTrends(SocorroMiddleware):

    def get(self, start_date=None, end_date=None,
            product='Firefox', version=None):
        params = {
            'product': product,
            'version': version,
            'start_date': start_date,
            'end_date': end_date
        }

        self.urlencode_params(params)
        url = ('/crashtrends/start_date/%(start_date)s/end_date/%(end_date)s'
               '/product/%(product)s/version/%(version)s' % params)

        return self.fetch(url)


class BugzillaAPI(SocorroCommon):
    base_url = settings.BZAPI_BASE_URL
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


class SignatureURLs(SocorroMiddleware):

    def get(self, signature, products, versions, start_date, end_date):
        values_separator = '+'
        product_versions = []
        for i, product in enumerate(products):
            product_versions.append('%s:%s' % (product, versions[i]))
        params = {
            'products': values_separator.join(products),
            'versions': values_separator.join(product_versions),
            'signature': signature,
            'start_date': start_date,
            'end_date': end_date,
        }
        self.urlencode_params(params)
        url = ('/signatureurls/signature/%(signature)s/'
               'start_date/%(start_date)s/end_date/%(end_date)s/'
               'products/%(products)s/versions/%(versions)s/' % params)
        return self.fetch(url)
