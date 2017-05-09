# -*- coding: utf-8 -*-

import copy
import csv
import datetime
import json
import random
import urlparse
from cStringIO import StringIO

import pyquery
import mock
from nose.tools import eq_, ok_

from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils import timezone
from django.contrib.auth.models import (
    Group,
    Permission
)
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType

from socorro.lib import BadArgumentError
from socorro.external.crashstorage_base import CrashIDNotFound

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats import models
from crashstats.crashstats.management import PERMISSIONS
from crashstats.supersearch.tests.common import (
    SUPERSEARCH_FIELDS_MOCKED_RESULTS,
)
from crashstats.supersearch.models import (
    SuperSearchFields,
    SuperSearchUnredacted,
)
from crashstats.crashstats.views import GRAPHICS_REPORT_HEADER
from .test_models import Response


SAMPLE_STATUS = {
    'breakpad_revision': '1035',
    'socorro_revision': '017d7b3f7042ce76bc80949ae55b41d1e915ab62',
    'schema_revision': 'schema_12345',
}

_SAMPLE_META = {
    'InstallTime': '1339289895',
    'FramePoisonSize': '4096',
    'Theme': 'classic/1.0',
    'Version': '5.0a1',
    'Email': 'some@emailaddress.com',
    'Vendor': 'Mozilla',
    'URL': 'someaddress.com'
}

_SAMPLE_UNREDACTED = {
    'client_crash_date': '2012-06-11T06:08:45',
    'signature': 'FakeSignature1',
    'uptime': 14693,
    'release_channel': 'nightly',
    'uuid': '11cb72f5-eb28-41e1-a8e4-849982120611',
    'flash_version': '[blank]',
    'hangid': None,
    'distributor_version': None,
    'truncated': True,
    'process_type': None,
    'id': 383569625,
    'os_version': '10.6.8 10K549',
    'version': '5.0a1',
    'build': '20120609030536',
    'ReleaseChannel': 'nightly',
    'addons_checked': None,
    'product': 'WaterWolf',
    'os_name': 'Mac OS X',
    'os_pretty_version': 'OS X 10.11',
    'last_crash': 371342,
    'date_processed': '2012-06-11T06:08:44',
    'cpu_name': 'amd64',
    'cpu_info': 'AuthenticAMD family 20 model 2 stepping 0 | 2 ',
    'reason': 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS',
    'address': '0x8',
    'completeddatetime': '2012-06-11T06:08:57',
    'success': True,
    'json_dump': {
        'status': 'OK',
        'sensitive': {
            'exploitability': 'high'
        },
        'threads': []
    }
}


SAMPLE_SIGNATURE_SUMMARY = {
    'reports': {
        'products': [
            {
                'version_string': '33.0a2',
                'percentage': '57.542',
                'report_count': 103,
                'product_name': 'Firefox'
            },
        ],
        'uptime': [
            {
                'category': '< 1 min',
                'percentage': '29.126',
                'report_count': 30
            }
        ],
        'architecture': [
            {
                'category': 'x86',
                'percentage': '100.000',
                'report_count': 103
            }
        ],
        'flash_version': [
            {
                'category': '[blank]',
                'percentage': '100.000',
                'report_count': 103
            }
        ],
        'graphics': [
            {
                'report_count': 24,
                'adapter_name': None,
                'vendor_hex': '0x8086',
                'percentage': '23.301',
                'vendor_name': None,
                'adapter_hex': '0x0166'
            }
        ],
        'distinct_install': [
            {
                'crashes': 103,
                'version_string': '33.0a2',
                'product_name': 'Firefox',
                'installations': 59
            }
        ],
        'devices': [
            {
                'cpu_abi': 'XXX',
                'manufacturer': 'YYY',
                'model': 'ZZZ',
                'version': '1.2.3',
                'report_count': 52311,
                'percentage': '48.440',
            }
        ],
        'os': [
            {
                'category': 'Windows 8.1',
                'percentage': '55.340',
                'report_count': 57
            }
        ],
        'process_type': [
            {
                'category': 'Browser',
                'percentage': '100.000',
                'report_count': 103
            }
        ],
        'exploitability': [
            {
                'low_count': 0,
                'high_count': 0,
                'null_count': 0,
                'none_count': 4,
                'report_date': '2014-08-12',
                'medium_count': 0
            }
        ]
    }
}


class RobotsTestViews(DjangoTestCase):

    @override_settings(ENGAGE_ROBOTS=True)
    def test_robots_txt(self):
        url = '/robots.txt'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/plain')
        ok_('Allow: /' in response.content)

    @override_settings(ENGAGE_ROBOTS=False)
    def test_robots_txt_disengage(self):
        url = '/robots.txt'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/plain')
        ok_('Disallow: /' in response.content)


class FaviconTestViews(DjangoTestCase):

    def test_favicon(self):
        response = self.client.get('/favicon.ico')
        eq_(response.status_code, 200)
        ok_(
            # the content type is dependent on the OS
            response['Content-Type'] in (
                'image/x-icon',  # most systems
                'image/vnd.microsoft.icon'  # jenkins for example
            )
        )


class BaseTestViews(DjangoTestCase):

    def setUp(self):
        super(BaseTestViews, self).setUp()

        # Tests assume and require a non-persistent cache backend
        assert 'LocMemCache' in settings.CACHES['default']['BACKEND']

        def mocked_platforms_get(**options):
            return {
                'hits': [
                    {
                        'code': 'win',
                        'name': 'Windows',
                    },
                    {
                        'code': 'mac',
                        'name': 'Mac OS X',
                    },
                    {
                        'code': 'lin',
                        'name': 'Linux',
                    }
                ],
                'total': 6
            }

        models.Platforms.implementation().get.side_effect = (
            mocked_platforms_get
        )

        def mocked_product_versions(**params):
            now = datetime.datetime.utcnow()
            yesterday = now - datetime.timedelta(days=1)

            end_date = now.strftime('%Y-%m-%d')
            yesterday = yesterday.strftime('%Y-%m-%d')

            hits = [
                # WaterWolfs
                {
                    'product': 'WaterWolf',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '19.0',
                    'build_type': 'Beta',
                    'has_builds': True,
                },
                {
                    'product': 'WaterWolf',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '18.0',
                    'build_type': 'Stable',
                    'has_builds': False,
                },
                {
                    'product': 'WaterWolf',
                    'throttle': '100.00',
                    'end_date': '2012-03-09',
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '19.1',
                    'build_type': 'Nightly',
                    'has_builds': True,
                },
                {
                    'product': 'WaterWolf',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '20.0',
                    'build_type': 'Nightly',
                    'has_builds': True,
                },
                # NightTrains
                {
                    'product': 'NightTrain',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '18.0',
                    'build_type': 'Aurora',
                    'has_builds': True,
                },
                {
                    'product': 'NightTrain',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '19.0',
                    'build_type': 'Nightly',
                    'has_builds': True,
                },
                # SeaMonkies
                {
                    'product': 'SeaMonkey',
                    'throttle': '99.00',
                    'end_date': yesterday,
                    'start_date': '2012-03-08',
                    'is_featured': False,
                    'version': '9.5',
                    'build_type': 'Alpha',
                    'has_builds': True,
                },
                {
                    'product': 'SeaMonkey',
                    'throttle': '99.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': False,
                    'version': '10.5',
                    'build_type': 'nightly',
                    'has_builds': True,
                },
                # LandCrab
                {
                    'product': 'LandCrab',
                    'throttle': '99.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': False,
                    'version': '1.5',
                    'build_type': 'Release',
                    'has_builds': False,
                },
            ]
            return {
                'hits': hits,
                'total': len(hits),
            }

        models.ProductVersions.implementation().get.side_effect = (
            mocked_product_versions
        )

        def mocked_supersearchfields(**params):
            results = copy.deepcopy(SUPERSEARCH_FIELDS_MOCKED_RESULTS)
            # to be realistic we want to introduce some dupes
            # that have a different key but its `in_database_name`
            # is one that is already in the hardcoded list (the
            # baseline)
            assert 'accessibility' not in results
            results['accessibility'] = {
                'name': 'accessibility',
                'query_type': 'string',
                'namespace': 'raw_crash',
                'form_field_choices': None,
                'permissions_needed': [],
                'default_value': None,
                'is_exposed': True,
                'is_returned': True,
                'is_mandatory': False,
                'in_database_name': 'Accessibility',
            }
            return results
        SuperSearchFields.implementation().get.side_effect = (
            mocked_supersearchfields
        )
        # This will make sure the cache is pre-populated
        SuperSearchFields().get()

        # call these here so it gets patched for each test because
        # it gets used so often

        models.ProductVersions().get(active=True)
        models.Platforms().get()

        def mocked_bugs_get(**options):
            return {
                'hits': [{
                    'id': '123456789',
                    'signature': 'Something'
                }]
            }

        # The default mocking of Bugs.get
        models.Bugs.implementation().get.side_effect = mocked_bugs_get

    def tearDown(self):
        super(BaseTestViews, self).tearDown()
        cache.clear()

        from crashstats.crashstats.models import SocorroCommon
        # We use a memoization technique on the SocorroCommon so that we
        # can get the same implementation class instance repeatedly under
        # the same request. This is great for low-level performance but
        # it makes it impossible to test classes that are imported only
        # once like they are in unit test running.
        SocorroCommon.clear_implementations_cache()

    def _add_permission(self, user, codename, group_name='Hackers'):
        group = self._create_group_with_permission(codename)
        user.groups.add(group)

    def _create_group_with_permission(self, codename, group_name='Group'):
        appname = 'crashstats'
        ct, __ = ContentType.objects.get_or_create(
            model='',
            app_label=appname,
            defaults={'name': appname}
        )
        permission, __ = Permission.objects.get_or_create(
            codename=codename,
            name=PERMISSIONS[codename],
            content_type=ct
        )
        group, __ = Group.objects.get_or_create(
            name=group_name,
        )
        group.permissions.add(permission)
        return group

    @staticmethod
    def only_certain_columns(hits, columns):
        """return a new list where each dict within only has keys mentioned
        in the `columns` list."""
        return [
            dict(
                (k, x[k])
                for k in x
                if k in columns
            )
            for x in hits
        ]


class TestViews(BaseTestViews):

    def test_contribute_json(self):
        response = self.client.get('/contribute.json')
        eq_(response.status_code, 200)
        # Should be valid JSON, but it's a streaming content because
        # it comes from django.views.static.serve
        ok_(json.loads(''.join(response.streaming_content)))
        eq_(response['Content-Type'], 'application/json')

    def test_handler500(self):
        root_urlconf = __import__(
            settings.ROOT_URLCONF,
            globals(),
            locals(),
            ['urls'],
            -1
        )
        # ...so that we can access the 'handler500' defined in there
        par, end = root_urlconf.handler500.rsplit('.', 1)
        # ...which is an importable reference to the real handler500 function
        views = __import__(par, globals(), locals(), [end], -1)
        # ...and finally we have the handler500 function at hand
        handler500 = getattr(views, end)

        # to make a mock call to the django view functions you need a request
        fake_request = RequestFactory().request(**{'wsgi.input': None})

        # the reason for first causing an exception to be raised is because
        # the handler500 function is only called by django when an exception
        # has been raised which means sys.exc_info() is something.
        try:
            raise NameError('sloppy code')
        except NameError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            eq_(response.status_code, 500)
            ok_('Internal Server Error' in response.content)
            ok_('id="products_select"' not in response.content)

    def test_handler500_json(self):
        root_urlconf = __import__(
            settings.ROOT_URLCONF,
            globals(),
            locals(),
            ['urls'],
            -1
        )
        par, end = root_urlconf.handler500.rsplit('.', 1)
        views = __import__(par, globals(), locals(), [end], -1)
        handler500 = getattr(views, end)

        fake_request = RequestFactory().request(**{'wsgi.input': None})
        # This is what the utils.json_view decorator sets on views
        # that should eventually return JSON.
        fake_request._json_view = True

        try:
            raise NameError('sloppy code')
        except NameError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            eq_(response.status_code, 500)
            eq_(response['Content-Type'], 'application/json')
            result = json.loads(response.content)
            eq_(result['error'], 'Internal Server Error')
            eq_(result['path'], '/')
            eq_(result['query_string'], None)

    def test_handler404(self):
        url = reverse('home:home', args=('Unknown',))
        response = self.client.get(url)
        eq_(response.status_code, 404)
        ok_('Page Not Found' in response.content)
        ok_('id="products_select"' not in response.content)

    def test_handler404_json(self):
        # Just need any view that has the json_view decorator on it.
        url = reverse('api:model_wrapper', args=('Unknown',))
        response = self.client.get(url, {'foo': 'bar'})
        eq_(response.status_code, 404)
        eq_(response['Content-Type'], 'application/json')
        result = json.loads(response.content)
        eq_(result['error'], 'Page not found')
        eq_(result['path'], url)
        eq_(result['query_string'], 'foo=bar')

    @mock.patch('requests.Session')
    def test_buginfo(self, rsession):
        url = reverse('crashstats:buginfo')

        def mocked_get(url, **options):
            if 'bug?id=123,456' in url:
                return Response({
                    'bugs': [{
                        'id': 123,
                        'status': 'NEW',
                        'resolution': '',
                        'summary': 'Some Summary',
                    }, {
                        'id': 456,
                        'status': 'NEW',
                        'resolution': '',
                        'summary': 'Other Summary',
                    }],
                })

            raise NotImplementedError(url)

        rsession().get.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_ids': ''})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_ids': ' 123, 456 '})
        eq_(response.status_code, 200)

        struct = json.loads(response.content)
        ok_(struct['bugs'])
        eq_(struct['bugs'][0]['summary'], 'Some Summary')

    @mock.patch('requests.Session')
    def test_buginfo_with_caching(self, rsession):
        url = reverse('crashstats:buginfo')

        def mocked_get(url, **options):
            if 'bug?id=987,654' in url:
                return Response({
                    'bugs': [
                        {
                            'id': '987',
                            'product': 'allizom.org',
                            'summary': 'Summary 1',
                        },
                        {
                            'id': '654',
                            'product': 'mozilla.org',
                            'summary': 'Summary 2',
                        }
                    ]
                })

            raise NotImplementedError(url)

        rsession().get.side_effect = mocked_get

        response = self.client.get(url, {
            'bug_ids': '987,654',
            'include_fields': 'product,summary'
        })
        eq_(response.status_code, 200)
        struct = json.loads(response.content)

        eq_(struct['bugs'][0]['product'], 'allizom.org')
        eq_(struct['bugs'][0]['summary'], 'Summary 1')
        eq_(struct['bugs'][0]['id'], '987')
        eq_(struct['bugs'][1]['product'], 'mozilla.org')
        eq_(struct['bugs'][1]['summary'], 'Summary 2')
        eq_(struct['bugs'][1]['id'], '654')

        # expect to be able to find this in the cache now
        cache_key = 'buginfo:987'
        eq_(cache.get(cache_key), struct['bugs'][0])

    def test_exploitability_report(self):
        url = reverse('crashstats:exploitability_report')

        def mocked_bugs_threesigs(**options):
            return {
                'hits': [
                    {'id': '111111111', 'signature': 'FakeSignature 1'},
                    {'id': '222222222', 'signature': 'FakeSignature 3'},
                    {'id': '101010101', 'signature': 'FakeSignature'}
                ]
            }

        models.Bugs.implementation().get.side_effect = mocked_bugs_threesigs

        queried_versions = []

        def mocked_supersearch_get(**params):
            eq_(params['product'], ['WaterWolf'])
            queried_versions.append(params.get('version'))
            eq_(params['_aggs.signature'], ['exploitability'])
            eq_(params['_facets_size'], settings.EXPLOITABILITY_BATCH_SIZE)
            ok_(params['exploitability'])
            assert params['_fields']
            facets = [
                {
                    'count': 229,
                    'facets': {
                        'exploitability': [
                            {'count': 210, 'term': u'none'},
                            {'count': 19, 'term': u'low'},
                        ]
                    },
                    'term': 'FakeSignature 1'
                },
                {
                    'count': 124,
                    'facets': {
                        'exploitability': [
                            {'count': 120, 'term': u'none'},
                            {'count': 1, 'term': 'high'},
                            {'count': 4, 'term': 'interesting'},
                        ]
                    },
                    'term': 'FakeSignature 3'
                },
                {
                    'count': 104,
                    'facets': {
                        'exploitability': [
                            {'count': 93, 'term': u'low'},
                            {'count': 11, 'term': u'medium'},
                        ]
                    },
                    'term': 'Other Signature',
                },
                {
                    'count': 222,
                    'facets': {
                        'exploitability': [
                            # one that doesn't add up to 4
                            {'count': 10, 'term': u'null'},
                            {'count': 20, 'term': u'none'},
                        ]
                    },
                    'term': 'FakeSignature',
                },
            ]
            return {
                'facets': {
                    'signature': facets,
                },
                'hits': [],
                'total': 1234
            }

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        response = self.client.get(url, {'product': 'WaterWolf'})
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.get(url, {'product': 'WaterWolf'})
        eq_(response.status_code, 302)

        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_exploitability')

        # unrecognized product
        response = self.client.get(url, {'product': 'XXXX'})
        eq_(response.status_code, 400)

        # unrecognized version
        response = self.client.get(
            url,
            {'product': 'WaterWolf', 'version': '0000'}
        )
        eq_(response.status_code, 400)

        # valid version but not for WaterWolf
        response = self.client.get(
            url,
            {'product': 'WaterWolf', 'version': '1.5'}
        )
        eq_(response.status_code, 400)

        # if you omit the product, it'll redirect and set the default product
        response = self.client.get(url)
        eq_(response.status_code, 302)

        ok_(response['Location'].endswith(
            url + '?product=%s' % settings.DEFAULT_PRODUCT
        ))

        response = self.client.get(
            url,
            {'product': 'WaterWolf', 'version': '19.0'}
        )
        eq_(response.status_code, 200)

        doc = pyquery.PyQuery(response.content)

        # We expect a table with 3 different signatures
        # The signature with the highest high+medium count is
        # 'Other Signature' etc.
        tds = doc('table.data-table tbody td:first-child a')
        texts = [x.text for x in tds]
        eq_(texts, ['Other Signature', 'FakeSignature 3', 'FakeSignature 1'])

        # The first signature doesn't have any bug associations,
        # but the second and the third does.
        rows = doc('table.data-table tbody tr')
        texts = [
            [x.text for x in doc('td.bug_ids_more a', row)]
            for row in rows
        ]
        eq_(
            texts,
            [
                [],
                ['222222222'],
                ['111111111']
            ]
        )

        assert queried_versions == [['19.0']]
        response = self.client.get(url, {'product': 'WaterWolf'})
        eq_(response.status_code, 200)

        assert queried_versions == [['19.0'], None]

    def test_crashes_per_day(self):
        url = reverse('crashstats:crashes_per_day')

        def mocked_adi_get(**options):
            eq_(options['versions'], ['20.0', '19.0'])
            end_date = timezone.now().date()
            # the default is two weeks
            start_date = end_date - datetime.timedelta(weeks=2)
            eq_(options['start_date'], start_date.strftime('%Y-%m-%d'))
            eq_(options['end_date'], end_date.strftime('%Y-%m-%d'))
            eq_(options['product'], 'WaterWolf')
            eq_(options['platforms'], ['Windows', 'Mac OS X', 'Linux'])
            response = {
                'total': 4,
                'hits': []
            }
            while start_date < end_date:
                for version in ['20.0', '19.0']:
                    for build_type in ['beta', 'release']:
                        response['hits'].append({
                            'adi_count': long(random.randint(100, 1000)),
                            'build_type': build_type,
                            'date': start_date,
                            'version': version
                        })
                start_date += datetime.timedelta(days=1)
            return response

        def mocked_product_build_types_get(**options):
            return {
                'hits': {
                    'release': 0.1,
                    'beta': 1.0,
                }
            }

        models.ProductBuildTypes.implementation().get.side_effect = (
            mocked_product_build_types_get
        )

        models.ADI.implementation().get.side_effect = mocked_adi_get

        def mocked_supersearch_get(**params):
            eq_(params['product'], ['WaterWolf'])
            eq_(params['version'], ['20.0', '19.0'])
            end_date = timezone.now().date()
            start_date = end_date - datetime.timedelta(weeks=2)  # the default
            expected_dates = [
                start_date.strftime('>=%Y-%m-%d'),
                end_date.strftime('<%Y-%m-%d'),
            ]
            eq_(params['date'], expected_dates)
            eq_(params['_histogram.date'], ['version'])
            eq_(params['_facets'], ['version'])
            eq_(params['_results_number'], 0)
            eq_(params['_columns'], ('date', 'version', 'platform', 'product'))
            assert params['_fields']

            response = {
                'facets': {
                    'histogram_date': [],
                    'signature': [],
                    'version': []
                },
                'hits': [],
                'total': 21187
            }
            totals = {
                '19.0': 0,
                '20.0': 0,
            }
            while start_date < end_date:
                counts = dict(
                    (version, random.randint(0, 100))
                    for version in ['20.0', '19.0']
                )
                date = {
                    'count': sum(counts.values()),
                    'facets': {
                        'version': [
                            {'count': v, 'term': k}
                            for k, v in counts.items()
                        ]
                    },
                    'term': start_date.isoformat()
                }
                for version, count in counts.items():
                    totals[version] += count
                response['facets']['histogram_date'].append(date)
                start_date += datetime.timedelta(days=1)
            response['facets']['version'] = [
                {'count': v, 'term': k}
                for k, v in totals.items()
            ]
            return response

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        response = self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['20.0', '19.0']
        })
        eq_(response.status_code, 200)

        # There's not a whole lot we can easily test in the output
        # because it's random numbers in the mock functions
        # and trying to not use random numbers and looking for
        # exact sums or whatnot is error prone because we might
        # asset that the number appears anywhere.
        doc = pyquery.PyQuery(response.content)
        # Table headers for each version
        th_texts = [x.text for x in doc('th')]
        ok_('19.0' in th_texts)
        ok_('20.0' in th_texts)

        # There should be 14 days worth of content in the main table.
        # Plus two for the standard headers
        eq_(doc('table.crash_data tr').size(), 14 + 2)

        # check that the CSV version is working too
        response = self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['20.0', '19.0'],
            'format': 'csv'
        })
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/csv')

        # also, I should be able to read it
        reader = csv.reader(response)
        # because response is an iterator that will return a blank line first
        # we skip till the next time
        rows = list(reader)[1:]
        eq_(len(rows), 14 + 1)  # +1 for the header
        head_row = rows[0]
        eq_(
            head_row,
            [
                'Date',
                'WaterWolf 20.0 Crashes',
                'WaterWolf 20.0 ADI',
                'WaterWolf 20.0 Throttle',
                'WaterWolf 20.0 Ratio',
                'WaterWolf 19.0 Crashes',
                'WaterWolf 19.0 ADI',
                'WaterWolf 19.0 Throttle',
                'WaterWolf 19.0 Ratio'
            ]
        )
        first_row = rows[1]
        yesterday = timezone.now() - datetime.timedelta(days=1)

        def is_percentage(thing):
            try:
                float(thing.replace('%', ''))
                return thing.endswith('%')
            except ValueError:
                return False

        eq_(first_row[0], yesterday.strftime('%Y-%m-%d'))
        ok_(first_row[1].isdigit())  # crashes
        ok_(first_row[2].isdigit())  # adi
        ok_(is_percentage(first_row[3]))  # throttle
        ok_(is_percentage(first_row[4]))  # ratio

    def test_crashes_per_day_product_sans_featured_versions(self):
        url = reverse('crashstats:crashes_per_day')

        def mocked_adi_get(**options):
            eq_(options['versions'], ['9.5', '10.5'])
            response = {
                'total': 0,
                'hits': []
            }
            return response

        models.ADI.implementation().get.side_effect = mocked_adi_get

        def mocked_product_build_types_get(**options):
            return {
                'hits': {
                    'release': 0.1,
                    'beta': 1.0,
                }
            }

        models.ProductBuildTypes.implementation().get.side_effect = (
            mocked_product_build_types_get
        )

        def mocked_supersearch_get(**params):
            eq_(params['product'], ['SeaMonkey'])
            eq_(params['version'], ['9.5', '10.5'])
            response = {
                'facets': {
                    'histogram_date': [],
                    'signature': [],
                    'version': []
                },
                'hits': [],
                'total': 0
            }
            return response

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        response = self.client.get(url, {
            'p': 'SeaMonkey',
            # Note that no version is passed explicitly
        })
        eq_(response.status_code, 200)
        # Not going to do more testing of the response content. That's
        # what test_crashes_per_day() does.
        # This tests' mocking methods checks that the right versions
        # (9.5 and 10.5) are pulled out for the various data queries.

    def test_crashes_per_day_failing_shards(self):
        url = reverse('crashstats:crashes_per_day')

        def mocked_adi_get(**options):
            return {
                'total': 0,
                'hits': []
            }

        models.ADI.implementation().get.side_effect = mocked_adi_get

        def mocked_product_build_types_get(**options):
            return {
                'hits': {
                    'release': 0.1,
                    'beta': 1.0,
                }
            }

        models.ProductBuildTypes.implementation().get.side_effect = (
            mocked_product_build_types_get
        )

        def mocked_supersearch_get(**params):
            return {
                'facets': {
                    'histogram_date': [],
                    'signature': [],
                    'version': []
                },
                'hits': [],
                'total': 21187,
                'errors': [
                    {
                        'type': 'shards',
                        'index': 'socorro201001',
                        'shards_count': 2,
                    }
                ],
            }

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        response = self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['20.0', '19.0']
        })
        eq_(response.status_code, 200)

        ok_('Our database is experiencing troubles' in response.content)
        ok_('week of 2010-01-04 is ~20% lower' in response.content)

    def test_crashes_per_day_bad_argument_error(self):
        url = reverse('crashstats:crashes_per_day')

        def mocked_adi_get(**options):
            return {
                'total': 0,
                'hits': []
            }

        models.ADI.implementation().get.side_effect = mocked_adi_get

        def mocked_product_build_types_get(**options):
            return {
                'hits': {
                    'release': 0.1,
                    'beta': 1.0,
                }
            }

        models.ProductBuildTypes.implementation().get.side_effect = (
            mocked_product_build_types_get
        )

        def mocked_supersearch_get(**params):
            raise BadArgumentError('Someone is wrong on the Internet')

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        response = self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['20.0', '19.0']
        })
        eq_(response.status_code, 400)
        ok_('Someone is wrong on the Internet' in response.content)

    def test_crashes_per_day_legacy_by_build_date(self):
        url = reverse('crashstats:crashes_per_day')

        response = self.client.get(url, {
            'date_range_type': 'build',
            'product': 'Whatever',
            'foo': 'bar'
        })
        # If we use self.assertRedirects() it will actually go to the
        # redirected URL which we haven't set up mocking for yet.
        eq_(response.status_code, 302)
        redirect_url = response['Location']
        parsed = urlparse.urlparse(redirect_url)
        eq_(parsed.path, url)
        ok_('product=Whatever'in parsed.query)
        ok_('foo=bar'in parsed.query)
        ok_('date_range_type=build' not in parsed.query)
        ok_('date_range_type=' not in parsed.query)

    def test_crashes_per_day_with_beta_versions(self):
        """This is a variation on test_crashes_per_day() (above)
        but with fewer basic assertions. The point of this
        test is to request it for '18.0b' and '19.0'. The '18.0b'
        is actual a beta version that needs to be exploded into its
        actual releases which are, in this test '18.0b1' and '18.0b2'.
        """

        # Important trick. If we don't do this, since the ProductVersions
        # model is mocked out in setUp, we can't change the result
        # for this one particular test.
        models.ProductVersions.cache_seconds = 0

        url = reverse('crashstats:crashes_per_day')

        def mocked_adi_get(**options):
            eq_(options['versions'], ['19.0', '18.0b1', '18.0b'])
            end_date = timezone.now().date()
            # the default is two weeks
            start_date = end_date - datetime.timedelta(weeks=2)
            response = {
                'total': 4,
                'hits': []
            }
            while start_date < end_date:
                for version in ['18.0b1', '18.0b2', '19.0']:
                    for build_type in ['beta', 'release']:
                        response['hits'].append({
                            'adi_count': long(random.randint(100, 1000)),
                            'build_type': build_type,
                            'date': start_date,
                            'version': version
                        })
                start_date += datetime.timedelta(days=1)
            return response

        models.ADI.implementation().get.side_effect = mocked_adi_get

        def mocked_product_build_types_get(**options):
            return {
                'hits': {
                    'release': 0.1,
                    'beta': 1.0,
                }
            }

        models.ProductBuildTypes.implementation().get.side_effect = (
            mocked_product_build_types_get
        )

        def mocked_product_versions(**params):
            end_date = timezone.now().strftime('%Y-%m-%d')
            hits = [
                {
                    'product': 'WaterWolf',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '19.0',
                    'build_type': 'Beta',
                },
                {
                    'product': 'WaterWolf',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '18.0b1',
                    'build_type': 'Beta',
                },
                {
                    'product': 'WaterWolf',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '18.0b',
                    'build_type': 'Beta',
                },
                {
                    'product': 'WaterWolf',
                    'throttle': '100.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
                    'version': '18.0b2',
                    'build_type': 'Beta',
                }
            ]
            return {
                'hits': hits,
                'total': len(hits),
            }

        models.ProductVersions.implementation().get.side_effect = (
            mocked_product_versions
        )

        def mocked_supersearch_get(**params):
            eq_(params['product'], ['WaterWolf'])
            eq_(params['version'], ['19.0', '18.0b1', '18.0b'])
            end_date = timezone.now().date()
            start_date = end_date - datetime.timedelta(weeks=2)  # the default
            assert params['_fields']

            response = {
                'facets': {
                    'histogram_date': [],
                    'signature': [],
                    'version': []
                },
                'hits': [],
                'total': 21187
            }
            totals = {
                '18.0b1': 0,
                '18.0b2': 0,
                '19.0': 0,
            }
            while start_date < end_date:
                counts = dict(
                    (version, random.randint(0, 100))
                    for version in ['18.0b1', '18.0b2', '19.0']
                )
                date = {
                    'count': sum(counts.values()),
                    'facets': {
                        'version': [
                            {'count': v, 'term': k}
                            for k, v in counts.items()
                        ]
                    },
                    'term': start_date.isoformat()
                }
                for version, count in counts.items():
                    totals[version] += count
                response['facets']['histogram_date'].append(date)
                start_date += datetime.timedelta(days=1)
            response['facets']['version'] = [
                {'count': v, 'term': k}
                for k, v in totals.items()
            ]
            return response

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        response = self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['18.0b', '19.0', '18.0b1']
        })
        eq_(response.status_code, 200)

        # There's not a whole lot we can easily test in the output
        # because it's random numbers in the mock functions
        # and trying to not use random numbers and looking for
        # exact sums or whatnot is error prone because we might
        # asset that the number appears anywhere.
        doc = pyquery.PyQuery(response.content)
        # Table headers for each version
        th_texts = [x.text for x in doc('th')]
        ok_('19.0' in th_texts)
        ok_('18.0b' in th_texts)
        ok_('18.0b1' in th_texts)
        ok_('18.0b2' not in th_texts)

        # There should be 14 days worth of content in the main table.
        # Plus two for the standard headers
        eq_(doc('table.crash_data tr').size(), 14 + 2)

    def test_quick_search(self):
        url = reverse('crashstats:quick_search')

        # Test with no parameter.
        response = self.client.get(url)
        eq_(response.status_code, 302)
        target = reverse('supersearch.search')
        ok_(response['location'].endswith(target))

        # Test with a signature.
        response = self.client.get(
            url,
            {'query': 'moz'}
        )
        eq_(response.status_code, 302)
        target = reverse('supersearch.search') + '?signature=%7Emoz'
        ok_(response['location'].endswith(target))

        # Test with a crash_id.
        crash_id = '1234abcd-ef56-7890-ab12-abcdef130802'
        response = self.client.get(
            url,
            {'query': crash_id}
        )
        eq_(response.status_code, 302)
        target = reverse(
            'crashstats:report_index',
            kwargs=dict(crash_id=crash_id)
        )
        ok_(response['location'].endswith(target))

        # Test a simple search containing a crash id and spaces
        crash_id = '   1234abcd-ef56-7890-ab12-abcdef130802 '
        response = self.client.get(
            url,
            {'query': crash_id}
        )
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(target))

    def test_status_redirect(self):
        response = self.client.get(reverse('crashstats:status_redirect'))
        correct_url = reverse('monitoring:index')
        eq_(response.status_code, 301)
        ok_(response['location'].endswith(correct_url))

    def test_status_revision(self):
        def mocked_get(**options):
            return SAMPLE_STATUS

        models.Status.implementation().get.side_effect = mocked_get

        url = reverse('crashstats:status_revision')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.content, '017d7b3f7042ce76bc80949ae55b41d1e915ab62')
        ok_('text/plain' in response['content-type'])

    def test_login_required(self):
        url = reverse(
            'crashstats:exploitability_report',
        )
        response = self.client.get(url)
        eq_(response.status_code, 302)
        ok_(settings.LOGIN_URL in response['Location'] + '?next=%s' % url)

    def test_crontabber_state(self):
        url = reverse('crashstats:crontabber_state')
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_report_index(self):
        dump = 'OS|Mac OS X|10.6.8 10K549\nCPU|amd64|family 6 mod|1'
        comment0 = 'This is a comment\nOn multiple lines'
        comment0 += '\npeterbe@example.com'
        comment0 += '\nwww.p0rn.com'

        def mocked_bugs_get(**options):
            return {
                'hits': [
                    {'id': '222222', 'signature': 'FakeSignature1'},
                    {'id': '333333', 'signature': 'FakeSignature1'},
                    {'id': '444444', 'signature': 'Other FakeSignature'}
                ]
            }
        models.Bugs.implementation().get.side_effect = mocked_bugs_get

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['dump'] = dump
                crash['user_comments'] = comment0
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # which bug IDs appear is important and the order matters too
        ok_(
            -1 ==
            response.content.find('444444') <
            response.content.find('333333') <
            response.content.find('222222')
        )

        ok_('FakeSignature1' in response.content)
        ok_('11cb72f5-eb28-41e1-a8e4-849982120611' in response.content)

        # Verify the "AMD CPU bug" marker is there.
        ok_('Possible AMD CPU bug related crash report' in response.content)

        comment_transformed = (
            comment0
            .replace('\n', '<br />')
            .replace('peterbe@example.com', '(email removed)')
            .replace('www.p0rn.com', '(URL removed)')
        )

        ok_(comment_transformed in response.content)
        # but the email should have been scrubbed
        ok_('peterbe@example.com' not in response.content)
        ok_(_SAMPLE_META['Email'] not in response.content)
        ok_(_SAMPLE_META['URL'] not in response.content)
        ok_(
            'You need to be signed in to download raw dumps.'
            in response.content
        )
        ok_(
            'You need to be signed in to view unredacted crashes.'
            in response.content
        )
        # Should not be able to see sensitive key from stackwalker JSON
        ok_('&#34;sensitive&#34;' not in response.content)
        ok_('&#34;exploitability&#34;' not in response.content)

        # The pretty platform version should appear.
        ok_('OS X 10.11' in response.content)

        # the email address will appear if we log in
        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_pii')

        response = self.client.get(url)
        ok_('peterbe@example.com' in response.content)
        ok_(_SAMPLE_META['Email'] in response.content)
        ok_(_SAMPLE_META['URL'] in response.content)
        ok_('&#34;sensitive&#34;' in response.content)
        ok_('&#34;exploitability&#34;' in response.content)
        eq_(response.status_code, 200)

        # Ensure fields have their description in title.
        ok_('No description for this field.' in response.content)
        ok_('Description of the signature field' in response.content)

        # If the user ceases to be active, these PII fields should disappear
        user.is_active = False
        user.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('peterbe@example.com' not in response.content)
        ok_(_SAMPLE_META['Email'] not in response.content)
        ok_(_SAMPLE_META['URL'] not in response.content)

    def test_report_index_with_raw_crash_unicode_key(self):

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                raw = copy.deepcopy(_SAMPLE_META)
                raw[u'Prénom'] = 'Peter'
                return raw
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        # Be signed in with view_pii to avoid whitelisting
        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_pii')

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # The response is a byte string so look for 'Pr\xc3\xa9nom' in the
        # the client output.
        ok_(u'Prénom'.encode('utf-8') in response.content)

    def test_report_index_with_additional_raw_dump_links(self):
        # using \\n because it goes into the JSON string
        dump = 'OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1'

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params

            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                del crash['json_dump']
                crash['dump'] = dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params

            if params['datatype'] == 'meta':
                return {
                    'InstallTime': '1339289895',
                    'FramePoisonSize': '4096',
                    'Theme': 'classic/1.0',
                    'Version': '5.0a1',
                    'Email': 'secret@email.com',
                    'Vendor': 'Mozilla',
                    'URL': 'farmville.com',
                    'additional_minidumps': 'foo, bar,',
                }

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        url = reverse('crashstats:report_index', args=(crash_id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # first of all, expect these basic URLs
        raw_json_url = reverse('crashstats:raw_data', args=(crash_id, 'json'))
        raw_dmp_url = reverse('crashstats:raw_data', args=(crash_id, 'dmp'))
        # not quite yet
        ok_(raw_json_url not in response.content)
        ok_(raw_dmp_url not in response.content)

        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # still they don't appear
        ok_(raw_json_url not in response.content)
        ok_(raw_dmp_url not in response.content)

        group = self._create_group_with_permission('view_rawdump')
        user.groups.add(group)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # finally they appear
        ok_(raw_json_url in response.content)
        ok_(raw_dmp_url in response.content)

        # also, check that the other links are there
        foo_dmp_url = reverse(
            'crashstats:raw_data_named',
            args=(crash_id, 'upload_file_minidump_foo', 'dmp')
        )
        ok_(foo_dmp_url in response.content)
        bar_dmp_url = reverse(
            'crashstats:raw_data_named',
            args=(crash_id, 'upload_file_minidump_bar', 'dmp')
        )
        ok_(bar_dmp_url in response.content)

    def test_report_index_with_symbol_url_in_modules(self):
        json_dump = {
            'status': 'OK',
            'sensitive': {
                'exploitability': 'high'
            },
            'threads': [],
            'modules': [
                {
                    'base_addr': '0x769c0000',
                    'code_id': '411096B9b3000',
                    'debug_file': 'userenv.pdb',
                    'debug_id': 'C72199CE55A04CD2A965557CF1D97F4E2',
                    'end_addr': '0x76a73000',
                    'filename': 'userenv.dll',
                    'version': '5.1.2600.2180',
                },
                {
                    'base_addr': '0x76b40000',
                    'code_id': '411096D62d000',
                    'debug_file': 'winmm.pdb',
                    'debug_id': '4FC9F179964745CAA3C78D6FADFC28322',
                    'end_addr': '0x76b6d000',
                    'filename': 'winmm.dll',
                    'loaded_symbols': True,
                    'symbol_disk_cache_hit': True,
                    'symbol_url': 'https://s3.example.com/winmm.sym',
                    'version': '5.1.2600.2180',
                },
            ]
        }

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                crash = copy.deepcopy(_SAMPLE_META)
                crash['additional_minidumps'] = 'foo, bar,'
                return crash
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['json_dump'] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        url = reverse('crashstats:report_index', args=(crash_id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        assert 'id="modules-list"' in response.content
        ok_(
            '<a href="https://s3.example.com/winmm.sym">winmm.dll</a>' in
            response.content
        )

    def test_report_index_with_shutdownhang_signature(self):
        json_dump = {
            'crash_info': {
                'crashing_thread': 2,
            },
            'status': 'OK',
            'threads': [
                {'frame_count': 0, 'frames': []},
                {'frame_count': 0, 'frames': []},
                {'frame_count': 0, 'frames': []},
            ],
            'modules': [],
        }

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['json_dump'] = json_dump
                crash['signature'] = 'shutdownhang | foo::bar()'
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        url = reverse('crashstats:report_index', args=(crash_id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('Crashing Thread (2)' not in response.content)
        ok_('Crashing Thread (0)' in response.content)

    def test_report_index_fennecandroid_report(self):
        comment0 = 'This is a comment\nOn multiple lines'
        comment0 += '\npeterbe@mozilla.com'
        comment0 += '\nwww.p0rn.com'

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['product'] = 'WinterSun'
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])

        bug_product_map = {
            'WinterSun': 'Winter Is Coming'
        }
        with self.settings(BUG_PRODUCT_MAP=bug_product_map):
            response = self.client.get(url)
            eq_(response.status_code, 200)
            doc = pyquery.PyQuery(response.content)

            link = doc('#bugzilla a[target="_blank"]').eq(0)
            eq_(link.text(), 'Winter Is Coming')
            ok_('product=Winter+Is+Coming' in link.attr('href'))

            # also, the "More Reports" link should have WinterSun in it
            link = doc('a.sig-overview').eq(0)
            ok_('product=WinterSun' in link.attr('href'))

    def test_report_index_odd_product_and_version(self):
        """If the processed JSON references an unfamiliar product and
        version it should not use that to make links in the nav to
        reports for that unfamiliar product and version."""
        comment0 = 'This is a comment\nOn multiple lines'
        comment0 += '\npeterbe@mozilla.com'
        comment0 += '\nwww.p0rn.com'

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['product'] = 'SummerWolf'
                crash['version'] = '99.9'
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # the title should have the "SummerWolf 99.9" in it
        doc = pyquery.PyQuery(response.content)
        title = doc('title').text()
        ok_('SummerWolf' in title)
        ok_('99.9' in title)

        # there shouldn't be any links to reports for the product
        # mentioned in the processed JSON
        bad_url = reverse('home:home', args=('SummerWolf',))
        ok_(bad_url not in response.content)

    def test_report_index_no_dump(self):

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                del crash['json_dump']
                return crash

            raise NotImplementedError(url)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('No dump available' in response.content)

    def test_report_index_invalid_crash_id(self):
        # last 6 digits indicate 30th Feb 2012 which doesn't exist
        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120230'])
        response = self.client.get(url)
        eq_(response.status_code, 400)
        ok_('Invalid crash ID' in response.content)
        eq_(response['Content-Type'], 'text/html; charset=utf-8')

    def test_report_index_with_valid_install_time(self):

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return {
                    'InstallTime': '1461170304',
                    'Version': '5.0a1',
                }

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            'crashstats:report_index',
            args=['11cb72f5-eb28-41e1-a8e4-849982120611']
        )
        response = self.client.get(url)
        ok_('Install Time</th>' in response.content)
        # This is what 1461170304 is in human friendly format.
        ok_('2016-04-20 16:38:24' in response.content)

    def test_report_index_with_invalid_install_time(self):

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                crash = copy.deepcopy(_SAMPLE_META)
                crash['InstallTime'] = 'Not a number'
                return crash

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            'crashstats:report_index',
            args=['11cb72f5-eb28-41e1-a8e4-849982120611']
        )
        response = self.client.get(url)
        # The heading is there but there should not be a value for it
        doc = pyquery.PyQuery(response.content)
        # Look for a <tr> whose <th> is 'Install Time', then
        # when we've found the row, we look at the text of its <td> child.
        for row in doc('#details tr'):
            if pyquery.PyQuery(row).find('th').text() == 'Install Time':
                eq_(pyquery.PyQuery(row).find('td').text(), '')

    def test_report_index_empty_os_name(self):

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['os_name'] = None
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            'crashstats:report_index',
            args=['11cb72f5-eb28-41e1-a8e4-849982120611']
        )
        response = self.client.get(url)
        # Despite the `os_name` being null, it should work to render
        # this page.
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        for node in doc('#mainbody'):
            eq_(node.attrib['data-platform'], '')

    def test_report_index_with_invalid_parsed_dump(self):
        json_dump = {
            'crash_info': {
                'address': '0x88',
                'type': 'EXCEPTION_ACCESS_VIOLATION_READ'
            },
            'main_module': 0,
            'modules': [
                {
                    'base_addr': '0x980000',
                    'debug_file': 'FlashPlayerPlugin.pdb',
                    'debug_id': '5F3C0D3034CA49FE9B94FC97EBF590A81',
                    'end_addr': '0xb4d000',
                    'filename': 'FlashPlayerPlugin_13_0_0_214.exe',
                    'version': '13.0.0.214'},
            ],
            'sensitive': {'exploitability': 'none'},
            'status': 'OK',
            'system_info': {
                'cpu_arch': 'x86',
                'cpu_count': 8,
                'cpu_info': 'GenuineIntel family 6 model 26 stepping 4',
                'os': 'Windows NT',
                'os_ver': '6.0.6002 Service Pack 2'
            },
            'thread_count': 1,
            'threads': [{'frame_count': 0, 'frames': []}]
        }

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['json_dump'] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        ok_('<th>Install Time</th>' not in response.content)

    def test_report_index_with_sparse_json_dump(self):
        json_dump = {'status': 'ERROR_NO_MINIDUMP_HEADER', 'sensitive': {}}

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['json_dump'] = json_dump
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_report_index_with_crash_exploitability(self):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['exploitability'] = 'Unknown Exploitability'
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index', args=[crash_id])

        response = self.client.get(url)
        ok_('Exploitability</th>' not in response.content)

        # you must be signed in to see exploitability
        user = self._login()
        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)

        response = self.client.get(url)
        ok_('Exploitability</th>' in response.content)
        ok_('Unknown Exploitability' in response.content)

    def test_report_index_your_crash(self):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                copied = copy.deepcopy(_SAMPLE_META)
                copied['Email'] = 'peterbe@example.com'
                copied['URL'] = 'https://embarrassing.example.com'
                return copied

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['exploitability'] = 'Unknown Exploitability'
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index', args=[crash_id])

        response = self.client.get(url)
        ok_('Exploitability</th>' not in response.content)
        ok_('peterbe@example.com' not in response.content)
        ok_('https://embarrassing.example.com' not in response.content)

        # you must be signed in to see exploitability
        self._login(email='peterbe@example.com')
        response = self.client.get(url)
        ok_('Exploitability</th>' in response.content)
        ok_('Unknown Exploitability' in response.content)
        ok_('peterbe@example.com' in response.content)
        ok_('https://embarrassing.example.com' in response.content)

    def test_report_index_not_your_crash(self):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                copied = copy.deepcopy(_SAMPLE_META)
                copied['Email'] = 'peterbe@example.com'
                copied['URL'] = 'https://embarrassing.example.com'
                return copied

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['exploitability'] = 'Unknown Exploitability'
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index', args=[crash_id])

        # You sign in, but a different email address from that in the
        # raw crash. Make sure that doesn't show the sensitive data
        self._login(email='someone@example.com')
        response = self.client.get(url)
        ok_('Exploitability</th>' not in response.content)
        ok_('Unknown Exploitability' not in response.content)
        ok_('peterbe@example.com' not in response.content)
        ok_('https://embarrassing.example.com' not in response.content)

    def test_report_index_raw_crash_not_found(self):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                raise CrashIDNotFound(params['uuid'])

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 404)
        ok_('Crash Not Found' in response.content)

    def test_report_index_processed_crash_not_found(self):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                raise CrashIDNotFound(params['uuid'])

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        def mocked_priority_job_process(**params):
            assert params['crash_ids'] == [crash_id]
            return True

        models.Priorityjob.implementation().process.side_effect = (
            mocked_priority_job_process
        )

        url = reverse('crashstats:report_index', args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_('Please wait...' in response.content)
        ok_(
            'Processing this crash report only takes a few seconds' in
            response.content
        )

    def test_report_index_with_invalid_date_processed(self):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                # NOTE! A wanna-be valid date that is not valid
                crash['date_processed'] = '2015-10-10 15:32:07.620535'
                return crash
            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index', args=[crash_id])

        response = self.client.get(url)
        # The date could not be converted in the jinja helper
        # to a more human format.
        ok_('2015-10-10 15:32:07.620535' in response.content)

    def test_report_index_redirect_by_prefix(self):

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        base_crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        crash_id = settings.CRASH_ID_PREFIX + base_crash_id
        assert len(crash_id) > 36
        url = reverse('crashstats:report_index', args=[crash_id])
        response = self.client.get(url)
        correct_url = reverse('crashstats:report_index', args=[base_crash_id])
        self.assertRedirects(response, correct_url)

    def test_report_index_with_thread_name(self):
        """Some threads now have a name. If there is one, verify that name is
        displayed next to that thread's number.
        """
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        json_dump = {
            'crash_info': {
                'crashing_thread': 1,
            },
            'thread_count': 2,
            'threads': [{
                'frame_count': 0,
                'frames': [],
                'thread_name': 'I am a Regular Thread',
            }, {
                'frame_count': 0,
                'frames': [],
                'thread_name': 'I am a Crashing Thread',
            }],
        }

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash['json_dump'] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index', args=[crash_id])

        response = self.client.get(url)
        ok_(
            'Crashing Thread (1), Name: I am a Crashing Thread' in
            response.content
        )
        ok_('Thread 0, Name: I am a Regular Thread' in response.content)

    def test_raw_data(self):

        def mocked_get(**params):
            if 'datatype' in params and params['datatype'] == 'raw':
                return "bla bla bla"
            else:
                # default is datatype/meta
                return {
                    'foo': 'bar',
                    'stuff': 123,
                }

        models.RawCrash.implementation().get.side_effect = mocked_get

        crash_id = '176bcd6c-c2ec-4b0c-9d5f-dadea2120531'
        json_url = reverse('crashstats:raw_data', args=(crash_id, 'json'))
        response = self.client.get(json_url)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % json_url
        )
        eq_(response.status_code, 302)

        user = self._login()
        group = self._create_group_with_permission('view_rawdump')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_rawdump')

        response = self.client.get(json_url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/json')
        eq_(json.loads(response.content),
            {'foo': 'bar', 'stuff': 123})

        dump_url = reverse('crashstats:raw_data', args=(crash_id, 'dmp'))
        response = self.client.get(dump_url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/octet-stream')
        ok_('bla bla bla' in response.content, response.content)

        # dump files are cached.
        # check the mock function and expect no change
        def different_mocked_get(**params):
            raise AssertionError("shouldn't be used due to caching")

        models.RawCrash.implementation().get.side_effect = different_mocked_get

        response = self.client.get(dump_url)
        eq_(response.status_code, 200)
        ok_('bla bla bla' in response.content)  # still. good.

    def test_raw_data_memory_report(self):

        crash_id = '176bcd6c-c2ec-4b0c-9d5f-dadea2120531'

        def mocked_get(**params):
            assert params['name'] == 'memory_report'
            assert params['uuid'] == crash_id
            assert params['datatype'] == 'raw'
            return "binary stuff"

        models.RawCrash.implementation().get.side_effect = mocked_get

        dump_url = reverse(
            'crashstats:raw_data_named',
            args=(crash_id, 'memory_report', 'json.gz')
        )
        response = self.client.get(dump_url)
        eq_(response.status_code, 302)
        assert 'login' in response['Location']

        user = self._login()
        group = self._create_group_with_permission('view_rawdump')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_rawdump')

        response = self.client.get(dump_url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/octet-stream')
        ok_('binary stuff' in response.content, response.content)

    def test_unauthenticated_user_redirected_from_protected_page(self):
        url = reverse(
            'crashstats:exploitability_report',
        )
        response = self.client.get(url)
        self.assertRedirects(
            response,
            '%s?%s=%s' % (
                reverse('crashstats:login'),
                REDIRECT_FIELD_NAME,
                url,
            )
        )

    def test_login_page_renders(self):
        url = reverse('crashstats:login')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Login Required' in response.content)
        ok_('Insufficient Privileges' not in response.content)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Login Required' not in response.content)
        ok_('Insufficient Privileges' in response.content)

    def test_graphics_report(self):

        def mocked_get(**options):
            assert options['product'] == settings.DEFAULT_PRODUCT
            hits = [
                {
                    'signature': 'my signature',
                    'date_processed': '2015-10-08 23:22:21'
                },
                {
                    'signature': 'other signature',
                    'date_processed': '2015-10-08 13:12:11'
                },
            ]
            # value for each of these needs to be in there
            # supplement missing ones from the fixtures we intend to return
            for hit in hits:
                for head in GRAPHICS_REPORT_HEADER:
                    if head not in hit:
                        hit[head] = None
            return {
                'hits': hits,
                'total': len(hits)
            }

        models.GraphicsReport.implementation().get.side_effect = (
            mocked_get
        )

        url = reverse('crashstats:graphics_report')

        # viewing this report requires that you're signed in
        response = self.client.get(url)
        eq_(response.status_code, 403)

        # But being signed in isn't good enough, you need the right
        # permissions too.
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 403)

        # give the user the right permission
        group = Group.objects.create(name='Hackers')
        permission = Permission.objects.get(codename='run_long_queries')
        group.permissions.add(permission)
        user.groups.add(group)

        # But even with the right permissions you still need to
        # provide the right minimal parameters.
        response = self.client.get(url)
        eq_(response.status_code, 400)

        # Let's finally get it right. Permission AND the date parameter.
        data = {'date': datetime.datetime.utcnow().date()}
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/csv')
        eq_(response['Content-Length'], str(len(response.content)))

        # the response content should be parseable
        length = len(response.content)
        inp = StringIO(response.content)
        reader = csv.reader(inp, delimiter='\t')
        lines = list(reader)
        assert len(lines) == 3
        header = lines[0]
        eq_(header, list(GRAPHICS_REPORT_HEADER))
        first = lines[1]
        eq_(
            first[GRAPHICS_REPORT_HEADER.index('signature')],
            'my signature'
        )
        eq_(
            first[GRAPHICS_REPORT_HEADER.index('date_processed')],
            '2015-10-08 23:22:21'
        )

        # now fetch it with gzip
        response = self.client.get(url, data, HTTP_ACCEPT_ENCODING='gzip')
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/csv')
        eq_(response['Content-Length'], str(len(response.content)))
        eq_(response['Content-Encoding'], 'gzip')
        ok_(len(response.content) < length)

    def test_graphics_report_not_available_via_regular_web_api(self):
        # check that the model isn't available in the API documentation
        api_url = reverse('api:model_wrapper', args=('GraphicsReport',))
        response = self.client.get(reverse('api:documentation'))
        eq_(response.status_code, 200)
        ok_(api_url not in response.content)

    def test_about_throttling(self):
        # the old url used to NOT have a trailing slash
        response = self.client.get('/about/throttling')
        eq_(response.status_code, 301)
        self.assertRedirects(
            response,
            reverse('crashstats:about_throttling'),
            status_code=301
        )
