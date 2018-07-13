# -*- coding: utf-8 -*-

import re
import copy
import csv
import datetime
import json
from cStringIO import StringIO

import pyquery
import mock

from django.test import Client
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import (
    Group,
    Permission
)
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType

from socorro.external.crashstorage_base import CrashIDNotFound

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats import models
from crashstats.crashstats.signals import PERMISSIONS
from crashstats.supersearch.models import (
    SuperSearchFields,
    SuperSearchUnredacted,
    SuperSearch,
)
from crashstats.crashstats.views import GRAPHICS_REPORT_HEADER
from .test_models import Response
from socorro.external.es.super_search_fields import FIELDS


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
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/plain'
        assert 'Allow: /' in response.content

    @override_settings(ENGAGE_ROBOTS=False)
    def test_robots_txt_disengage(self):
        url = '/robots.txt'
        response = self.client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/plain'
        assert 'Disallow: /' in response.content


class FaviconTestViews(DjangoTestCase):

    def test_favicon(self):
        response = self.client.get('/favicon.ico')
        assert response.status_code == 200
        # the content type is dependent on the OS
        expected = (
            'image/x-icon',  # most systems
            'image/vnd.microsoft.icon'  # jenkins for example
        )
        assert response['Content-Type'] in expected


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
            results = copy.deepcopy(FIELDS)
            # to be realistic we want to introduce some dupes that have a
            # different key but its `in_database_name` is one that is already
            # in the hardcoded list (the baseline)
            results['accessibility2'] = results['accessibility']
            return results

        supersearchfields_mock_get = mock.Mock()
        supersearchfields_mock_get.side_effect = mocked_supersearchfields
        SuperSearchFields.get = supersearchfields_mock_get

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
        assert response.status_code == 200
        # Should be valid JSON, but it's a streaming content because
        # it comes from django.views.static.serve
        assert json.loads(''.join(response.streaming_content))
        assert response['Content-Type'] == 'application/json'

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
            assert response.status_code == 500
            assert 'Internal Server Error' in response.content
            assert 'id="products_select"' not in response.content

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
            assert response.status_code == 500
            assert response['Content-Type'] == 'application/json'
            result = json.loads(response.content)
            assert result['error'] == 'Internal Server Error'
            assert result['path'] == '/'
            assert result['query_string'] is None

    def test_handler404(self):
        response = self.client.get('/fillbert/mcpicklepants')
        assert response.status_code == 404
        assert 'The requested page could not be found.' in response.content

    def test_handler404_json(self):
        # Just need any view that has the json_view decorator on it.
        url = reverse('api:model_wrapper', args=('Unknown',))
        response = self.client.get(url, {'foo': 'bar'})
        assert response.status_code == 404
        assert response['Content-Type'] == 'application/json'
        result = json.loads(response.content)
        assert result['error'] == 'Page not found'
        assert result['path'] == url
        assert result['query_string'] == 'foo=bar'

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
        assert response.status_code == 400

        response = self.client.get(url, {'bug_ids': ''})
        assert response.status_code == 400

        response = self.client.get(url, {'bug_ids': ' 123, 456 '})
        assert response.status_code == 200

        struct = json.loads(response.content)
        assert struct['bugs']
        assert struct['bugs'][0]['summary'] == 'Some Summary'

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
        assert response.status_code == 200
        struct = json.loads(response.content)

        assert struct['bugs'][0]['product'] == 'allizom.org'
        assert struct['bugs'][0]['summary'] == 'Summary 1'
        assert struct['bugs'][0]['id'] == '987'
        assert struct['bugs'][1]['product'] == 'mozilla.org'
        assert struct['bugs'][1]['summary'] == 'Summary 2'
        assert struct['bugs'][1]['id'] == '654'

        # expect to be able to find this in the cache now
        cache_key = 'buginfo:987'
        assert cache.get(cache_key) == struct['bugs'][0]

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
            assert params['product'] == ['WaterWolf']
            queried_versions.append(params.get('version'))
            assert params['_aggs.signature'] == ['exploitability']
            assert params['_facets_size'] == settings.EXPLOITABILITY_BATCH_SIZE
            assert params['exploitability']
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
        assert response.status_code == 302

        user = self._login()
        response = self.client.get(url, {'product': 'WaterWolf'})
        assert response.status_code == 302

        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_exploitability')

        # unrecognized product
        response = self.client.get(url, {'product': 'XXXX'})
        assert response.status_code == 400

        # unrecognized version
        response = self.client.get(
            url,
            {'product': 'WaterWolf', 'version': '0000'}
        )
        assert response.status_code == 400

        # valid version but not for WaterWolf
        response = self.client.get(
            url,
            {'product': 'WaterWolf', 'version': '1.5'}
        )
        assert response.status_code == 400

        # if you omit the product, it'll redirect and set the default product
        response = self.client.get(url)
        assert response.status_code == 302

        assert response['Location'].endswith(url + '?product=%s' % settings.DEFAULT_PRODUCT)

        response = self.client.get(
            url,
            {'product': 'WaterWolf', 'version': '19.0'}
        )
        assert response.status_code == 200

        doc = pyquery.PyQuery(response.content)

        # We expect a table with 3 different signatures
        # The signature with the highest high+medium count is
        # 'Other Signature' etc.
        tds = doc('table.data-table tbody td:first-child a')
        texts = [x.text for x in tds]
        assert texts == ['Other Signature', 'FakeSignature 3', 'FakeSignature 1']

        # The first signature doesn't have any bug associations,
        # but the second and the third does.
        rows = doc('table.data-table tbody tr')
        texts = [
            [x.text for x in doc('td.bug_ids_more a', row)]
            for row in rows
        ]
        expected = [
            [],
            ['222222222'],
            ['111111111']
        ]
        assert texts == expected

        assert queried_versions == [['19.0']]
        response = self.client.get(url, {'product': 'WaterWolf'})
        assert response.status_code == 200
        assert queried_versions == [['19.0'], None]

    def test_quick_search(self):
        url = reverse('crashstats:quick_search')

        # Test with no parameter.
        response = self.client.get(url)
        assert response.status_code == 302
        target = reverse('supersearch.search')
        assert response['location'].endswith(target)

        # Test with a signature.
        response = self.client.get(
            url,
            {'query': 'moz'}
        )
        assert response.status_code == 302
        target = reverse('supersearch.search') + '?signature=%7Emoz'
        assert response['location'].endswith(target)

        # Test with a crash_id.
        crash_id = '1234abcd-ef56-7890-ab12-abcdef130802'
        response = self.client.get(
            url,
            {'query': crash_id}
        )
        assert response.status_code == 302
        target = reverse(
            'crashstats:report_index',
            kwargs=dict(crash_id=crash_id)
        )
        assert response['location'].endswith(target)

        # Test a simple search containing a crash id and spaces
        crash_id = '   1234abcd-ef56-7890-ab12-abcdef130802 '
        response = self.client.get(
            url,
            {'query': crash_id}
        )
        assert response.status_code == 302
        assert response['location'].endswith(target)

    def test_login_required(self):
        url = reverse(
            'crashstats:exploitability_report',
        )
        response = self.client.get(url)
        assert response.status_code == 302
        assert settings.LOGIN_URL in response['Location'] + '?next=%s' % url

    def test_crontabber_state(self):
        url = reverse('crashstats:crontabber_state')
        response = self.client.get(url)
        assert response.status_code == 200

    def test_report_index(self):
        json_dump = {
            'system_info': {
                'os': 'Mac OS X',
                'os_ver': '10.6.8 10K549',
                'cpu_arch': 'amd64',
                'cpu_info': 'family 6 mod',
                'cpu_count': 1
            },
            'sensitive': {
                'exploitability': 'high'
            }
        }
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
                crash['json_dump'] = json_dump
                crash['user_comments'] = comment0
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        assert response.status_code == 200
        # which bug IDs appear is important and the order matters too
        assert (
            -1 ==
            response.content.find('444444') <
            response.content.find('333333') <
            response.content.find('222222')
        )

        assert 'FakeSignature1' in response.content
        assert '11cb72f5-eb28-41e1-a8e4-849982120611' in response.content

        # Verify the "AMD CPU bug" marker is there.
        assert 'Possible AMD CPU bug related crash report' in response.content

        comment_transformed = (
            comment0
            .replace('\n', '<br />')
            .replace('peterbe@example.com', '(email removed)')
            .replace('www.p0rn.com', '(URL removed)')
        )

        assert comment_transformed in response.content
        # but the email should have been scrubbed
        assert 'peterbe@example.com' not in response.content
        assert _SAMPLE_META['Email'] not in response.content
        assert _SAMPLE_META['URL'] not in response.content
        assert 'You need to be signed in to download raw dumps.' in response.content
        assert 'You need to be signed in to view unredacted crashes.' in response.content
        # Should not be able to see sensitive key from stackwalker JSON
        assert '&#34;sensitive&#34;' not in response.content
        assert '&#34;exploitability&#34;' not in response.content

        # The pretty platform version should appear.
        assert 'OS X 10.11' in response.content

        # the email address will appear if we log in
        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_pii')

        response = self.client.get(url)
        assert 'peterbe@example.com' in response.content
        assert _SAMPLE_META['Email'] in response.content
        assert _SAMPLE_META['URL'] in response.content
        assert '&#34;sensitive&#34;' in response.content
        assert '&#34;exploitability&#34;' in response.content
        assert response.status_code == 200

        # Ensure fields have their description in title.
        assert 'No description for this field.' in response.content
        # NOTE(willkg): This is the description of "crash address". If we ever
        # change that we'll need to update this to another description that
        # shows up.
        assert 'The crashing address.' in response.content

        # If the user ceases to be active, these PII fields should disappear
        user.is_active = False
        user.save()
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'peterbe@example.com' not in response.content
        assert _SAMPLE_META['Email'] not in response.content
        assert _SAMPLE_META['URL'] not in response.content

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
        assert response.status_code == 200
        # The response is a byte string so look for 'Pr\xc3\xa9nom' in the
        # the client output.
        assert u'Prénom'.encode('utf-8') in response.content

    def test_report_index_with_refreshed_cache(self):

        raw_crash_calls = []

        def mocked_raw_crash_get(**params):
            raw_crash_calls.append(params)
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        processed_crash_calls = []

        def mocked_processed_crash_get(**params):
            processed_crash_calls.append(params)
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(raw_crash_calls) == len(processed_crash_calls) == 1

        # Call it a second time and the cache should kick in
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(raw_crash_calls) == len(processed_crash_calls) == 1  # same!

        response = self.client.get(url, {'refresh': 'cache'})
        assert response.status_code == 200
        assert len(raw_crash_calls) == len(processed_crash_calls) == 2

    def test_report_index_with_remote_type_raw_crash(self):
        """If a processed crash has a 'process_type' value *and*
        if the raw crash has as 'RemoteType' then both of these
        values should be displayed in the HTML.
        """

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                raw = copy.deepcopy(_SAMPLE_META)
                raw['RemoteType'] = 'java-applet'
                return raw
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = (
            mocked_raw_crash_get
        )

        def mocked_processed_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                processed = copy.deepcopy(_SAMPLE_UNREDACTED)
                processed['process_type'] = 'contentish'
                return processed

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            'crashstats:report_index',
            args=['11cb72f5-eb28-41e1-a8e4-849982120611']
        )
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'Process Type' in response.content
        # Expect that it displays '{process_type}\s+({raw_crash.RemoteType})'
        assert re.findall('contentish\s+\(java-applet\)', response.content)

    def test_report_index_with_additional_raw_dump_links(self):
        json_dump = {
            'system_info': {
                'os': 'Mac OS X',
                'os_ver': '10.6.8 10K549',
                'cpu_arch': 'amd64',
                'cpu_info': 'family 6 mod',
                'cpu_count': 1
            }
        }

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
        assert response.status_code == 200

        # first of all, expect these basic URLs
        raw_json_url = reverse('crashstats:raw_data', args=(crash_id, 'json'))
        raw_dmp_url = reverse('crashstats:raw_data', args=(crash_id, 'dmp'))
        # not quite yet
        assert raw_json_url not in response.content
        assert raw_dmp_url not in response.content

        user = self._login()
        response = self.client.get(url)
        assert response.status_code == 200
        # still they don't appear
        assert raw_json_url not in response.content
        assert raw_dmp_url not in response.content

        group = self._create_group_with_permission('view_rawdump')
        user.groups.add(group)
        response = self.client.get(url)
        assert response.status_code == 200
        # finally they appear
        assert raw_json_url in response.content
        assert raw_dmp_url in response.content

        # also, check that the other links are there
        foo_dmp_url = reverse(
            'crashstats:raw_data_named',
            args=(crash_id, 'upload_file_minidump_foo', 'dmp')
        )
        assert foo_dmp_url in response.content
        bar_dmp_url = reverse(
            'crashstats:raw_data_named',
            args=(crash_id, 'upload_file_minidump_bar', 'dmp')
        )
        assert bar_dmp_url in response.content

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
        assert response.status_code == 200

        assert 'id="modules-list"' in response.content
        assert '<a href="https://s3.example.com/winmm.sym">winmm.dll</a>' in response.content

    def test_report_index_with_cert_subject_in_modules(self):
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
                    'cert_subject': 'Microsoft Windows',
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
            ],
            'modules_contains_cert_info': True,
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
        assert response.status_code == 200

        assert 'id="modules-list"' in response.content
        assert re.search('<td>userenv\.pdb</td>\s*?<td></td>', response.content)
        assert re.search('<td>winmm\.pdb</td>\s*?<td>Microsoft Windows</td>', response.content)

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
        assert response.status_code == 200

        assert 'Crashing Thread (2)' not in response.content
        assert 'Crashing Thread (0)' in response.content

    def test_report_index_with_no_crashing_thread(self):
        """If the json_dump has no crashing thread available, do not display a
        specific crashing thread, but instead display all threads.

        """
        json_dump = {
            'crash_info': {},
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
                crash['signature'] = 'foo::bar()'
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        url = reverse('crashstats:report_index', args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        assert 'Crashing Thread' not in response.content
        assert 'Thread 0' in response.content
        assert 'Thread 1' in response.content
        assert 'Thread 2' in response.content

    def test_report_index_with_telemetry_environment(self):

        def mocked_raw_crash_get(**params):
            assert 'datatype' in params
            if params['datatype'] == 'meta':
                crash = copy.deepcopy(_SAMPLE_META)
                crash['TelemetryEnvironment'] = {
                    'key': ['values'],
                    'plainstring': 'I am a string',
                    'plainint': 12345,
                    'empty': [],
                    'foo': {
                        'keyA': 'AAA',
                        'keyB': 'BBB',
                    },
                }
                return crash
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

        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        url = reverse('crashstats:report_index', args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        assert 'Telemetry Environment' in response.content
        # it's non-trivial to check that the dict above is serialized
        # exactly like jinja does it so let's just check the data attribute
        # is there.
        assert 'id="telemetryenvironment-json"' in response.content

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
            assert response.status_code == 200
            doc = pyquery.PyQuery(response.content)

            link = doc('#bugzilla a[target="_blank"]').eq(0)
            assert link.text() == 'Winter Is Coming'
            assert 'product=Winter+Is+Coming' in link.attr('href')

            # also, the "More Reports" link should have WinterSun in it
            link = doc('a.sig-overview').eq(0)
            assert 'product=WinterSun' in link.attr('href')

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
        assert response.status_code == 200
        # the title should have the "SummerWolf 99.9" in it
        doc = pyquery.PyQuery(response.content)
        title = doc('title').text()
        assert 'SummerWolf' in title
        assert '99.9' in title

        # there shouldn't be any links to reports for the product
        # mentioned in the processed JSON
        bad_url = reverse('home:home', args=('SummerWolf',))
        assert bad_url not in response.content

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
        assert response.status_code == 200
        assert 'No dump available' in response.content

    def test_report_index_invalid_crash_id(self):
        # last 6 digits indicate 30th Feb 2012 which doesn't exist
        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120230'])
        response = self.client.get(url)
        assert response.status_code == 400
        assert 'Invalid crash ID' in response.content
        assert response['Content-Type'] == 'text/html; charset=utf-8'

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
        assert 'Install Time</th>' in response.content
        # This is what 1461170304 is in human friendly format.
        assert '2016-04-20 16:38:24' in response.content

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
                assert pyquery.PyQuery(row).find('td').text() == ''

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
        assert response.status_code == 200
        doc = pyquery.PyQuery(response.content)
        for node in doc('#mainbody'):
            assert node.attrib['data-platform'] == ''

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
        assert '<th>Install Time</th>' not in response.content

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
        assert response.status_code == 200

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
        assert 'Exploitability</th>' not in response.content

        # you must be signed in to see exploitability
        user = self._login()
        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)

        response = self.client.get(url)
        assert 'Exploitability</th>' in response.content
        assert 'Unknown Exploitability' in response.content

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
        assert 'Exploitability</th>' not in response.content
        assert 'peterbe@example.com' not in response.content
        assert 'https://embarrassing.example.com' not in response.content

        # you must be signed in to see exploitability
        self._login(email='peterbe@example.com')
        response = self.client.get(url)
        assert 'Exploitability</th>' in response.content
        assert 'Unknown Exploitability' in response.content
        assert 'peterbe@example.com' in response.content
        assert 'https://embarrassing.example.com' in response.content

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
        assert 'Exploitability</th>' not in response.content
        assert 'Unknown Exploitability' not in response.content
        assert 'peterbe@example.com' not in response.content
        assert 'https://embarrassing.example.com' not in response.content

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

        assert response.status_code == 404
        assert 'Crash Not Found' in response.content

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

        assert response.status_code == 200
        assert 'Please wait...' in response.content
        assert 'Processing this crash report only takes a few seconds' in response.content

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
        assert '2015-10-10 15:32:07.620535' in response.content

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
        assert 'Crashing Thread (1), Name: I am a Crashing Thread' in response.content
        assert 'Thread 0, Name: I am a Regular Thread' in response.content

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
        assert response.status_code == 302

        user = self._login()
        group = self._create_group_with_permission('view_rawdump')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_rawdump')

        response = self.client.get(json_url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        assert json.loads(response.content) == {'foo': 'bar', 'stuff': 123}

        dump_url = reverse('crashstats:raw_data', args=(crash_id, 'dmp'))
        response = self.client.get(dump_url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/octet-stream'
        assert 'bla bla bla' in response.content, response.content

        # dump files are cached.
        # check the mock function and expect no change
        def different_mocked_get(**params):
            raise AssertionError("shouldn't be used due to caching")

        models.RawCrash.implementation().get.side_effect = different_mocked_get

        response = self.client.get(dump_url)
        assert response.status_code == 200
        assert 'bla bla bla' in response.content  # still. good.

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
        assert response.status_code == 302
        assert 'login' in response['Location']

        user = self._login()
        group = self._create_group_with_permission('view_rawdump')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_rawdump')

        response = self.client.get(dump_url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/octet-stream'
        assert 'binary stuff' in response.content, response.content

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
        assert response.status_code == 200
        assert 'Login Required' in response.content
        assert 'Insufficient Privileges' not in response.content

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'Login Required' not in response.content
        assert 'Insufficient Privileges' in response.content

    def test_graphics_report(self):

        def mocked_supersearch_get(**params):
            assert params['product'] == [settings.DEFAULT_PRODUCT]
            hits = [
                {
                    'signature': 'my signature',
                    'date': '2015-10-08T23:22:21.1234 +00:00',
                    'cpu_name': 'arm',
                    'cpu_info': 'ARMv7 ARM',
                },
                {
                    'signature': 'other signature',
                    'date': '2015-10-08T13:12:11.1123 +00:00',
                    'cpu_info': 'something',
                    # note! no cpu_name
                },
            ]
            # Value for each of these needs to be in there
            # supplement missing ones from the fixtures we intend to return.
            for hit in hits:
                for head in GRAPHICS_REPORT_HEADER:
                    if head not in hit:
                        hit[head] = None
            return {
                'hits': hits,
                'total': 2
            }

        SuperSearch.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        url = reverse('crashstats:graphics_report')

        # viewing this report requires that you're signed in
        response = self.client.get(url)
        assert response.status_code == 403

        # But being signed in isn't good enough, you need the right
        # permissions too.
        user = self._login()
        response = self.client.get(url)
        assert response.status_code == 403

        # Add the user to the Hackers group which has run_long_queries
        # permission
        group = Group.objects.get(name='Hackers')
        user.groups.add(group)

        # But even with the right permissions you still need to
        # provide the right minimal parameters.
        response = self.client.get(url)
        assert response.status_code == 400

        # Let's finally get it right. Permission AND the date parameter.
        data = {'date': datetime.datetime.utcnow().date()}
        response = self.client.get(url, data)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert response['Content-Length'] == str(len(response.content))

        # the response content should be parseable
        length = len(response.content)
        inp = StringIO(response.content)
        reader = csv.reader(inp, delimiter='\t')
        lines = list(reader)
        assert len(lines) == 3
        header = lines[0]
        assert header == list(GRAPHICS_REPORT_HEADER)
        first = lines[1]
        assert first[GRAPHICS_REPORT_HEADER.index('signature')] == 'my signature'
        assert first[GRAPHICS_REPORT_HEADER.index('date_processed')] == '201510082322'

        # now fetch it with gzip
        response = self.client.get(url, data, HTTP_ACCEPT_ENCODING='gzip')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert response['Content-Length'] == str(len(response.content))
        assert response['Content-Encoding'] == 'gzip'
        assert len(response.content) < length

    def test_graphics_report_not_available_via_regular_web_api(self):
        # check that the model isn't available in the API documentation
        api_url = reverse('api:model_wrapper', args=('GraphicsReport',))
        response = self.client.get(reverse('api:documentation'))
        assert response.status_code == 200
        assert api_url not in response.content

    def test_about_throttling(self):
        # the old url used to NOT have a trailing slash
        response = self.client.get('/about/throttling')
        assert response.status_code == 301
        self.assertRedirects(
            response,
            reverse('crashstats:about_throttling'),
            status_code=301
        )


class TestDockerflow:
    def test_version_no_file(self, tmpdir):
        """Test with no version.json file"""
        # The tmpdir definitely doesn't have a version.json in it, so we use
        # that
        with override_settings(SOCORRO_ROOT=str(tmpdir)):
            client = Client()
            resp = client.get(reverse('crashstats:dockerflow_version'))
            assert resp.status_code == 200
            assert resp['Content-Type'] == 'application/json'
            assert resp.content == '{}'

    def test_version_with_file(self, tmpdir):
        """Test with a version.json file"""
        text = '{"commit": "d6ac5a5d2acf99751b91b2a3ca651d99af6b9db3"}'

        # Create the version.json file in the tmpdir
        version_json = tmpdir.join('version.json')
        version_json.write(text)

        with override_settings(SOCORRO_ROOT=str(tmpdir)):
            client = Client()
            resp = client.get(reverse('crashstats:dockerflow_version'))
            assert resp.status_code == 200
            assert resp['Content-Type'] == 'application/json'
            assert resp.content == text
