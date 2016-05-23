# -*- coding: utf-8 -*-

import copy
import csv
import datetime
import json
import urllib
import random
import urlparse

import pyquery
import mock

from cStringIO import StringIO
from nose.tools import eq_, ok_, assert_raises
from nose.plugins.skip import SkipTest
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils import timezone
from django.contrib.auth.models import (
    User,
    AnonymousUser,
    Group,
    Permission
)
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats import models, views
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
    'hits': [
        {
            'date_oldest_job_queued': '2012-09-28T20:39:33+00:00',
            'date_recently_completed': '2012-09-28T20:40:00+00:00',
            'processors_count': 1,
            'avg_wait_sec': 16.407,
            'waiting_job_count': 56,
            'date_created': '2012-09-28T20:40:02+00:00',
            'id': 410655,
            'avg_process_sec': 0.914149
        },
        {
            'date_oldest_job_queued': '2012-09-28T20:34:33+00:00',
            'date_recently_completed': '2012-09-28T20:35:00+00:00',
            'processors_count': 1,
            'avg_wait_sec': 13.8293,
            'waiting_job_count': 48,
            'date_created': '2012-09-28T20:35:01+00:00',
            'id': 410654,
            'avg_process_sec': 1.24177
        },
        {
            'date_oldest_job_queued': '2012-09-28T20:29:32+00:00',
            'date_recently_completed': '2012-09-28T20:30:01+00:00',
            'processors_count': 1,
            'avg_wait_sec': 14.8803,
            'waiting_job_count': 1,
            'date_created': '2012-09-28T20:30:01+00:00',
            'id': 410653,
            'avg_process_sec': 1.19637
        }
    ],
    'total': 12,
    'socorro_revision': '017d7b3f7042ce76bc80949ae55b41d1e915ab62',
    'schema_revision': 'schema_12345'
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

BUG_STATUS = {
    'hits': [
        {'id': '222222', 'signature': 'FakeSignature1'},
        {'id': '333333', 'signature': 'FakeSignature1'},
        {'id': '444444', 'signature': 'Other FakeSignature'}
    ]
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


# Helper mocks for several tests
def mocked_post_123(**options):
    return {
        'hits': [{
            'id': '123456789',
            'signature': 'Something'
        }]
    }


def mocked_post_threesigs(**options):
    return {
        'hits': [
            {'id': '111111111', 'signature': 'FakeSignature 1'},
            {'id': '222222222', 'signature': 'FakeSignature 3'},
            {'id': '101010101', 'signature': 'FakeSignature'}
        ]
    }


def mocked_post_nohits(**options):
    return {'hits': [], 'total': 0}


def mocked_post_threeothersigs(**options):
    return BUG_STATUS


class TestHelpFunctions(DjangoTestCase):
    def test_get_super_search_style_params(self):
        params_in = {
            'signature': 'foo',
            'product': ['WaterWolf'],
            'platform': 'Linux',
            'version': 'WaterWolf:1.0a2',
            'end_date': datetime.datetime(2000, 1, 8),
            'start_date': datetime.datetime(2000, 1, 1),
        }
        params_out = views.get_super_search_style_params(**params_in)
        params_exp = {
            'signature': 'foo',
            'product': ['WaterWolf'],
            'platform': 'Linux',
            'version': '1.0a2',
            'date': ['>=2000-01-08T00:00:00', '<2000-01-01T00:00:00'],
        }

        ok_(params_out, params_exp)


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

    @mock.patch('requests.get')
    def setUp(self, rget):
        super(BaseTestViews, self).setUp()

        if 'LocMemCache' not in settings.CACHES['default']['BACKEND']:
            raise ImproperlyConfigured(
                'The tests requires that you use LocMemCache when running'
            )

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
                    'is_featured': True,
                    'version': '9.5',
                    'build_type': 'Alpha',
                    'has_builds': True,
                },
                {
                    'product': 'SeaMonkey',
                    'throttle': '99.00',
                    'end_date': end_date,
                    'start_date': '2012-03-08',
                    'is_featured': True,
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
            results = copy.copy(SUPERSEARCH_FIELDS_MOCKED_RESULTS)
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

    def _login(self):
        user = User.objects.create_user('test', 'test@mozilla.com', 'secret')
        assert self.client.login(username='test', password='secret')
        return user

    def _logout(self):
        self.client.logout()

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


class TestAnalytics(BaseTestViews):

    @override_settings(GOOGLE_ANALYTICS_ID='xyz123')
    @override_settings(GOOGLE_ANALYTICS_DOMAIN='test.biz')
    def test_google_analytics(self):
        url = reverse('home:home', args=('WaterWolf',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('xyz123' in response.content)
        ok_('test.biz' in response.content)


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
        # Need a fake user for the persona bits on crashstats_base
        fake_request.user = AnonymousUser()

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
        ok_('Page not Found' in response.content)
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

    @mock.patch('requests.get')
    def test_buginfo(self, rget):
        url = reverse('crashstats:buginfo')

        def mocked_get(url, params, **options):
            if 'bug?id=' in url:
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

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_ids': ''})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_ids': ' 123, 456 '})
        eq_(response.status_code, 200)

        struct = json.loads(response.content)
        ok_(struct['bugs'])
        eq_(struct['bugs'][0]['summary'], 'Some Summary')

    @mock.patch('requests.get')
    def test_buginfo_with_caching(self, rget):
        url = reverse('crashstats:buginfo')

        def mocked_get(url, params, **options):
            if 'bug?id=' in url:
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

        rget.side_effect = mocked_get

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

    def test_gccrashes(self):
        url = reverse('crashstats:gccrashes', args=('WaterWolf',))
        unknown_product_url = reverse('crashstats:gccrashes',
                                      args=('NotKnown',))
        invalid_version_url = reverse('crashstats:gccrashes',
                                      args=('WaterWolf', '99'))

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Total Volume of GC Crashes for WaterWolf 19.1'
            in response.content)

        response = self.client.get(invalid_version_url)
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        eq_(doc('.django-form-error li b')[0].text, 'Version:')

        response = self.client.get(unknown_product_url)
        eq_(response.status_code, 404)

    def test_gccrashes_json(self):
        url = reverse('crashstats:gccrashes_json')

        def mocked_get(**options):
            return {
                'hits': [
                    ['20140203000001', 366]
                ],
                'total': 1,
            }

        models.GCCrashes.implementation().get.side_effect = (
            mocked_get
        )

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': '2014-01-27',
            'end_date': '2014-02-04'
        })

        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])

    def test_gccrashes_json_bad_request(self):
        url = reverse('crashstats:gccrashes_json')

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': 'XXXXXX',  # not even close
            'end_date': '2014-02-04'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': '2014-02-33',  # crazy date
            'end_date': '2014-02-04'
        })
        eq_(response.status_code, 400)

        # same but on the end_date
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': '2014-02-13',
            'end_date': '2014-02-44'  # crazy date
        })
        eq_(response.status_code, 400)

        # start_date > end_date
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': '2014-02-02',
            'end_date': '2014-01-01'  # crazy date
        })
        eq_(response.status_code, 400)

    def test_get_nightlies_for_product_json(self):
        url = reverse('crashstats:get_nightlies_for_product_json')

        def mocked_product_versions(**options):
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

        models.ProductVersions.cache_seconds = 0

        models.ProductVersions.implementation().get.side_effect = (
            mocked_product_versions
        )

        response = self.client.get(url, {'product': 'WaterWolf'})
        ok_('application/json' in response['content-type'])
        eq_(response.status_code, 200)
        ok_(response.content, ['20.0'])

        response = self.client.get(url, {'product': 'NightTrain'})
        eq_(response.status_code, 200)
        ok_(response.content, ['18.0', '19.0'])

        response = self.client.get(url, {'product': 'Unknown'})
        ok_(response.content, [])

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_topcrasher(self, rget, rpost):
        # first without a version
        no_version_url = reverse('crashstats:topcrasher',
                                 args=('WaterWolf',))
        url = reverse('crashstats:topcrasher',
                      args=('WaterWolf', '19.0'))
        has_builds_url = reverse('crashstats:topcrasher',
                                 args=('WaterWolf', '19.0', 'build'))
        reports_count_default = reverse('crashstats:topcrasher',
                                        args=('WaterWolf', '19.0'))
        reports_count_100 = reverse('crashstats:topcrasher',
                                    args=('WaterWolf', '19.0', None, None,
                                          None, '100'))
        response = self.client.get(no_version_url)
        ok_(url in response['Location'])

        def mocked_post(**options):
            return {
                'hits': [
                   {'id': 123456789,
                    'signature': 'Something'},
                    {'id': 22222,
                     'signature': u'FakeSignature1 \u7684 Japanese'},
                    {'id': 33333,
                     'signature': u'FakeSignature1 \u7684 Japanese'}
                ]
            }
        rpost.side_effect = mocked_post

        def mocked_get(url, params, **options):
            if '/crashes/signatures' in url:
                return Response({
                    'crashes': [
                        {
                            'count': 188,
                            'mac_count': 66,
                            'content_count': 0,
                            'first_report': '2012-06-21',
                            'startup_percent': 0.0,
                            'currentRank': 0,
                            'previousRank': 1,
                            'first_report_exact': '2012-06-21T21:28:08',
                            'versions': (
                                '2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, '
                                '4.0a2, 5.0a1'
                            ),
                            'percentOfTotal': 0.24258064516128999,
                            'win_count': 56,
                            'changeInPercentOfTotal': 0.011139597126354983,
                            'linux_count': 66,
                            'hang_count': 0,
                            'signature': u'FakeSignature1 \u7684 Japanese',
                            'versions_count': 8,
                            'changeInRank': 1,
                            'plugin_count': 0,
                            'previousPercentOfTotal': 0.23144104803493501,
                            'is_gc_count': 10
                        }
                    ],
                    'totalPercentage': 0,
                    'start_date': '2012-05-10',
                    'end_date': '2012-05-24',
                    'totalNumberOfCrashes': 0,
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        def mocked_product_versions(**params):
            hits = [
                {
                    'is_featured': True,
                    'throttle': 1.0,
                    'end_date': 'string',
                    'start_date': 'integer',
                    'build_type': 'string',
                    'product': 'WaterWolf',
                    'version': '19.0',
                    'has_builds': True
                }
            ]
            return {
                'hits': hits,
                'total': len(hits),
            }

        models.ProductVersions.cache_seconds = 0

        models.ProductVersions.implementation().get.side_effect = (
            mocked_product_versions
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('By Crash Date' in response.content)

        response = self.client.get(has_builds_url)
        eq_(response.status_code, 200)
        ok_('By Build Date' in response.content)

        response = self.client.get(reports_count_default)
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        eq_(selected_count.text(), '50')

        # there's actually only one such TD
        bug_ids = [x.text for x in doc('td.bug_ids_more > a')]
        # higher bug number first
        eq_(bug_ids, ['33333', '22222'])

        response = self.client.get(reports_count_100)
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        eq_(selected_count.text(), '100')

        # also, render the CSV
        response = self.client.get(url, {'format': 'csv'})
        eq_(response.status_code, 200)
        ok_('text/csv' in response['Content-Type'])
        # know your fixtures :)
        ok_('WaterWolf' in response['Content-Disposition'])
        ok_('19.0' in response['Content-Disposition'])
        # we should be able unpack it
        reader = csv.reader(StringIO(response.content))
        line1, line2 = reader
        eq_(line1[0], 'Rank')
        try:
            eq_(int(line2[0]), 1)
        except Exception:
            raise SkipTest
        # bytestring when exported as CSV with UTF-8 encoding
        eq_(line2[4], 'FakeSignature1 \xe7\x9a\x84 Japanese')

    def test_topcrasher_with_invalid_version(self):
        # 0.1 is not a valid release version
        url = reverse('crashstats:topcrasher',
                      args=('WaterWolf', '0.1'))
        response = self.client.get(url)
        eq_(response.status_code, 302)

    def test_topcrasher_with_product_sans_release(self):

        def mocked_product_versions(**params):
            assert params['active']
            return {'hits': [], 'total': 0}

        models.ProductVersions.cache_seconds = 0
        models.ProductVersions.implementation().get.side_effect = (
            mocked_product_versions
        )

        # SnowLion is not a product at all
        url = reverse('crashstats:topcrasher',
                      args=('SnowLion', '0.1'))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        # SeaMonkey is a product but has no active releases
        url = reverse('crashstats:topcrasher',
                      args=('SeaMonkey', '9.5'))
        response = self.client.get(url)
        eq_(response.status_code, 404)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_topcrasher_without_any_signatures(self, rget, rpost):
        # first without a version
        no_version_url = reverse('crashstats:topcrasher',
                                 args=('WaterWolf',))
        url = reverse('crashstats:topcrasher',
                      args=('WaterWolf', '19.0'))
        has_builds_url = reverse('crashstats:topcrasher',
                                 args=('WaterWolf', '19.0', 'build'))
        response = self.client.get(no_version_url)
        ok_(url in response['Location'])

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if '/crashes/signatures' in url:
                return Response({
                    'crashes': [],
                    'totalPercentage': 0,
                    'start_date': '2012-05-10',
                    'end_date': '2012-05-24',
                    'totalNumberOfCrashes': 0,
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        def mocked_product_versions(**params):
            hits = [
                {
                    'is_featured': True,
                    'throttle': 1.0,
                    'end_date': 'string',
                    'start_date': 'integer',
                    'build_type': 'string',
                    'product': 'WaterWolf',
                    'version': '19.0',
                    'has_builds': True
                }
            ]
            return {'hits': hits, 'total': len(hits)}

        models.ProductVersions.cache_seconds = 0
        models.ProductVersions.implementation().get.side_effect = (
            mocked_product_versions
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('By Crash Date' in response.content)

        response = self.client.get(has_builds_url)
        eq_(response.status_code, 200)
        ok_('By Build Date' in response.content)

        # also, render the CSV
        response = self.client.get(url, {'format': 'csv'})
        eq_(response.status_code, 200)
        ok_('text/csv' in response['Content-Type'])
        # know your fixtures :)
        ok_('WaterWolf' in response['Content-Disposition'])
        ok_('19.0' in response['Content-Disposition'])
        #
        # no signatures, the CSV is empty apart from the header
        eq_(len(response.content.splitlines()), 1)
        reader = csv.reader(StringIO(response.content))
        line1, = reader
        eq_(line1[0], 'Rank')

    def test_topcrasher_without_versions_redirect(self):
        response = self.client.get('/topcrasher/products/WaterWolf/versions/')
        redirect_code = settings.PERMANENT_LEGACY_REDIRECTS and 301 or 302
        eq_(response.status_code, redirect_code)
        actual_url = reverse('crashstats:topcrasher',
                             kwargs={'product': 'WaterWolf'})
        ok_(response['location'].endswith(actual_url))

    @mock.patch('requests.get')
    def test_exploitable_crashes_without_product(self, rget):
        url = reverse('crashstats:exploitable_crashes_legacy')
        user = self._login()
        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_exploitability')

        response = self.client.get(url)
        eq_(response.status_code, 301)

        correct_url = reverse(
            'crashstats:exploitable_crashes',
            args=(settings.DEFAULT_PRODUCT,)
        )
        ok_(response['location'].endswith(correct_url))

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_exploitable_crashes(self, rget, rpost):
        url = reverse(
            'crashstats:exploitable_crashes',
            args=(settings.DEFAULT_PRODUCT,)
        )

        rpost.side_effect = mocked_post_threesigs

        def mocked_get(url, params, **options):
            assert '/crashes/exploitability' in url
            ok_('product' in params)
            eq_('WaterWolf', params['product'])

            return Response({
                'hits': [
                    {
                        'signature': 'FakeSignature',
                        'report_date': '2013-06-06',
                        'high_count': 4,
                        'medium_count': 3,
                        'low_count': 2,
                        'none_count': 1,
                        'product_name': settings.DEFAULT_PRODUCT,
                        'version_string': '2.0'
                    }
                ],
                'total': 1
            })
        rget.side_effect = mocked_get

        response = self.client.get(url)
        ok_(settings.LOGIN_URL in response['Location'] + '?next=%s' % url)
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 302)
        ok_(settings.LOGIN_URL in response['Location'] + '?next=%s' % url)

        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_exploitability')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('FakeSignature' in response.content)
        # only this bug ID should be shown
        ok_('101010101' in response.content)
        # not these bug IDs
        ok_('222222222' not in response.content)
        ok_('111111111' not in response.content)

        # if you try to mess with the paginator it should just load page 1
        response = self.client.get(url, {'page': 'meow'})
        eq_(response.status_code, 200)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_exploitable_crashes_by_product_and_version(self, rget, rpost):
        url = reverse(
            'crashstats:exploitable_crashes',
            args=(settings.DEFAULT_PRODUCT, '19.0')
        )

        rpost.side_effect = mocked_post_threesigs

        def mocked_get(url, params, **options):
            assert '/crashes/exploitability' in url
            ok_('product' in params)
            eq_('WaterWolf', params['product'])

            ok_('version' in params)
            eq_('19.0', params['version'])

            return Response({
                'hits': [
                    {
                        'signature': 'FakeSignature',
                        'report_date': '2013-06-06',
                        'high_count': 4,
                        'medium_count': 3,
                        'low_count': 2,
                        'none_count': 1,
                        'product_name': settings.DEFAULT_PRODUCT,
                        'version_string': '123.0'
                    }
                ],
                'total': 1
            })

        rget.side_effect = mocked_get

        user = self._login()
        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_exploitability')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('FakeSignature' in response.content)

    def test_exploitable_crashes_by_unknown_version(self):
        url = reverse(
            'crashstats:exploitable_crashes',
            args=(settings.DEFAULT_PRODUCT, '999.0')
        )
        user = self._login()
        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_exploitability')

        response = self.client.get(url)
        eq_(response.status_code, 302)
        home_url = reverse('home:home', args=(settings.DEFAULT_PRODUCT,))
        ok_(response['location'].endswith(home_url))

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    def test_exploitability_report(self, rpost):
        url = reverse('crashstats:exploitability_report')
        rpost.side_effect = mocked_post_threesigs

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

    @mock.patch('requests.get')
    def test_daily(self, rget):
        url = reverse('crashstats:daily')

        def mocked_get(url, params, **options):
            eq_(params['versions'], ['20.0', '19.0'])
            if '/products' in url:
                return Response({
                    'products': [
                        'WaterWolf',
                        'NightTrain'
                    ],
                    'hits': {
                        'WaterWolf': [{
                            'featured': True,
                            'throttle': 100.0,
                            'end_date': '2012-11-27',
                            'product': 'WaterWolf',
                            'release': 'Nightly',
                            'version': '19.0',
                            'has_builds': True,
                            'start_date': '2012-09-25'
                        }],
                        'NightTrain': [{
                            'featured': True,
                            'throttle': 100.0,
                            'end_date': '2012-11-27',
                            'product': 'NightTrain',
                            'release': 'Nightly',
                            'version': '18.0',
                            'has_builds': True,
                            'start_date': '2012-09-25'
                        }]
                    },
                    'total': 2
                })
            if '/crashes' in url:
                # This list needs to match the versions as done in the common
                # fixtures set up in setUp() above.
                return Response({
                    'hits': {
                        'WaterWolf:20.0': {
                            '2012-09-23': {
                                'adu': 80388,
                                'crash_hadu': 12.279,
                                'date': '2012-08-23',
                                'product': 'WaterWolf',
                                'report_count': 9871,
                                'throttle': 0.1,
                                'version': '20.0'
                            }
                        },
                        'WaterWolf:19.0': {
                            '2012-08-23': {
                                'adu': 80388,
                                'crash_hadu': 12.279,
                                'date': '2012-08-23',
                                'product': 'WaterWolf',
                                'report_count': 9871,
                                'throttle': 0.1,
                                'version': '19.0'
                            }
                        },
                        'WaterWolf:18.0': {
                            '2012-08-13': {
                                'adu': 80388,
                                'crash_hadu': 12.279,
                                'date': '2012-08-23',
                                'product': 'WaterWolf',
                                'report_count': 9871,
                                'throttle': 0.1,
                                'version': '18.0'
                            }
                        }
                    }
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['20.0', '19.0']
        })
        eq_(response.status_code, 200)
        # XXX any basic tests with can do on response.content?

        ok_('18.0' in response.content.split('id="version3"')[1].
            split("</select>")[0])
        ok_('18.0' in response.content.split('id="version2"')[1].
            split("</select>")[0])
        ok_('18.0' in response.content.split('id="version1"')[1].
            split("</select>")[0])
        ok_('18.0' in response.content.split('id="version0"')[1].
            split("</select>")[0])

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
        ok_(rows)
        head_row = rows[0]
        eq_(head_row[0], 'Date')
        eq_(
            head_row[1:],
            [
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
        eq_(first_row[0], '2012-09-23')

        # Test dates don't cause problems
        response = self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['20.0', '19.0'],
            'date_start': '2010-01-01'
        })
        eq_(response.status_code, 200)

        # Test that the version sorting is working
        self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['19.0', '20.0']
        })

        # Test that the versions become unique
        self.client.get(url, {
            'p': 'WaterWolf',
            'v': ['19.0', '19.0', '20.0']
        })

    def test_daily_legacy_redirect(self):
        url = reverse('crashstats:daily')
        response = self.client.get(url + '?p=WaterWolf&v[]=Something')
        eq_(response.status_code, 301)
        ok_('p=WaterWolf' in response['Location'].split('?')[1])
        ok_('v=Something' in response['Location'].split('?')[1])

        response = self.client.get(
            url + '?p=WaterWolf&os[]=Something&os[]=Else'
        )
        eq_(response.status_code, 301)
        ok_('p=WaterWolf' in response['Location'].split('?')[1])
        ok_('os=Something' in response['Location'].split('?')[1])
        ok_('os=Else' in response['Location'].split('?')[1])

    @mock.patch('requests.get')
    def test_daily_with_bad_input(self, rget):
        url = reverse('crashstats:daily')

        def mocked_get(url, params, **options):
            if '/products' in url:
                return Response({
                    'products': [
                        'WaterWolf',
                        'NightTrain'
                    ],
                    'hits': {
                        'WaterWolf': [{
                            'featured': True,
                            'throttle': 100.0,
                            'end_date': '2012-11-27',
                            'product': 'WaterWolf',
                            'release': 'Nightly',
                            'version': '19.0',
                            'has_builds': True,
                            'start_date': '2012-09-25'
                        }],
                        'NightTrain': [{
                            'featured': True,
                            'throttle': 100.0,
                            'end_date': '2012-11-27',
                            'product': 'NightTrain',
                            'release': 'Nightly',
                            'version': '18.0',
                            'has_builds': True,
                            'start_date': '2012-09-25'
                        }]
                    },
                    'total': 2
                })
            if '/crashes' in url:
                # This list needs to match the versions as done in the common
                # fixtures set up in setUp() above.
                return Response({
                    'hits': {}
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        response = self.client.get(url, {
            'p': 'WaterWolf',
            'date_start': u' \x00'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'p': 'WaterWolf',
            'date_range_type': 'any old crap'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'p': 'WaterWolf',
            'hang_type': 'any old crap'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'p': 'WaterWolf',
            'format': 'csv',
        })
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/csv')

        # last sanity check
        response = self.client.get(url, {
            'p': 'WaterWolf',
        })
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_crashes_per_day(self, rget):
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

    @mock.patch('requests.get')
    def test_crashes_per_day_with_beta_versions(self, rget):
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

        # put it back some something > 0
        models.CurrentProducts.cache_seconds = 60

    def test_crashes_per_user_redirect(self):
        """At some point in 2018 we can remove this test."""
        url = reverse('crashstats:crashes_per_user_redirect')
        destination_url = reverse('crashstats:crashes_per_day')

        response = self.client.get(url)
        eq_(response.status_code, 301)
        ok_(response['location'].endswith(destination_url))

        response = self.client.get(url, {'foo': 'bar'})
        eq_(response.status_code, 301)
        ok_(response['location'].endswith(destination_url + '?foo=bar'))

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

    @mock.patch('requests.get')
    def test_plot_signature(self, rget):
        def mocked_get(url, params, **options):
            if '/crashes/signature_history' in url:
                return Response({
                    'hits': [],
                    'total': 0
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        # missing signature
        url = reverse('crashstats:plot_signature',
                      args=('WaterWolf', '19.0',
                            '2011-12-01', '2011-12-02', ''))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        # invalid start date
        url = reverse('crashstats:plot_signature',
                      args=('WaterWolf', '19.0',
                            '2012-02-33', '2012-12-01',
                            'Read::Bytes'))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        # invalid end date
        url = reverse('crashstats:plot_signature',
                      args=('WaterWolf', '19.0',
                            '2012-02-28', '2012-13-01',
                            'Read::Bytes'))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        # valid dates
        url = reverse('crashstats:plot_signature',
                      args=('WaterWolf', '19.0',
                            '2011-12-01', '2011-12-02',
                            'Read::Bytes'))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        ok_(struct['signature'])

    @mock.patch('requests.get')
    def test_signature_summary(self, rget):
        def mocked_get(url, params, **options):
            if '/signaturesummary' in url:
                assert params['report_types']
                return Response({
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
                })
            raise NotImplementedError(url)

        url = reverse('crashstats:signature_summary')

        rget.side_effect = mocked_get

        # first try without the necessary parameters
        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'range_value': '1',
            'signature': 'sig',
            'version': 'WaterWolf:19.0'
        })
        eq_(response.status_code, 200)
        ok_('Operating System:' in response.content)
        ok_('Exploitability:' not in response.content)

        user = self._login()
        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)

        response = self.client.get(url, {
            'range_value': '1',
            'signature': 'sig',
            'version': 'WaterWolf:19.0'
        })
        eq_(response.status_code, 200)
        ok_('Operating System:' in response.content)
        ok_('Exploitability:' in response.content)

    @mock.patch('requests.get')
    def test_signature_summary_flash_exploitability(self, rget):
        def mocked_get(url, params, **options):
            signature_summary_data = copy.deepcopy(SAMPLE_SIGNATURE_SUMMARY)
            if '/signaturesummary' in url:
                if 'sig1' in params['signature']:
                    signature_summary_data['reports']['flash_version'] = [
                        {
                            'category': '11.9.900.117',
                            'percentage': '50.794',
                            'report_count': 320
                        },
                        {
                            'category': '11.9.900.152',
                            'percentage': '45.397',
                            'report_count': 286
                        },
                        {
                            'category': '11.7.700.224',
                            'percentage': '1.429',
                            'report_count': 9
                        }
                    ]
                elif 'sig2' in params['signature']:
                    signature_summary_data['reports']['flash_version'] = [
                        {
                            'category': '11.9.900.117',
                            'percentage': '50.794',
                            'report_count': 320
                        },
                        {
                            'category': '[blank]',
                            'percentage': '45.397',
                            'report_count': 286
                        },
                        {
                            'category': '11.7.700.224',
                            'percentage': '1.429',
                            'report_count': 9
                        }
                    ]

                return Response(signature_summary_data)
            raise NotImplementedError(url)

        url = reverse('crashstats:signature_summary')

        rget.side_effect = mocked_get

        user = self._login()
        group = self._create_group_with_permission('view_flash_exploitability')
        user.groups.add(group)

        response = self.client.get(url, {
            'range_value': '1',
            'signature': 'sig1',
            'version': 'WaterWolf:19.0'
        })
        eq_(response.status_code, 200)
        ok_('Exploitability:' in response.content)

        response = self.client.get(url, {
            'range_value': '1',
            'signature': 'sig2',  # different from before!
            'version': 'WaterWolf:19.0'
        })
        eq_(response.status_code, 200)
        ok_('Exploitability:' not in response.content)

    def test_status_redirect(self):
        response = self.client.get(reverse('crashstats:status_redirect'))
        correct_url = reverse('monitoring:index')
        eq_(response.status_code, 301)
        ok_(response['location'].endswith(correct_url))

    @mock.patch('requests.get')
    def test_status_revision(self, rget):
        def mocked_get(url, **options):
            assert '/server_status' in url, url
            return Response(SAMPLE_STATUS)

        rget.side_effect = mocked_get

        url = reverse('crashstats:status_revision')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.content, '017d7b3f7042ce76bc80949ae55b41d1e915ab62')
        ok_('text/plain' in response['content-type'])

    def test_login_required(self):
        url = reverse(
            'crashstats:exploitable_crashes',
            args=(settings.DEFAULT_PRODUCT,)
        )
        response = self.client.get(url)
        eq_(response.status_code, 302)
        ok_(settings.LOGIN_URL in response['Location'] + '?next=%s' % url)

    @mock.patch('requests.get')
    def test_status_json(self, rget):
        def mocked_get(**options):
            assert '/server_status' in options['url'], options['url']
            return Response(SAMPLE_STATUS)

        rget.side_effect = mocked_get

        url = reverse('crashstats:status_json')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_(response.content.strip().startswith('{'))
        ok_('017d7b3f7042ce76bc80949ae55b41d1e915ab62' in response.content)
        ok_('1035' in response.content)
        ok_('2012-09-28T20:30:01+00:00' in response.content)
        ok_('application/json' in response['Content-Type'])
        eq_('*', response['Access-Control-Allow-Origin'])

    def test_crontabber_state(self):
        url = reverse('crashstats:crontabber_state')
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index(self, rget, rpost):
        dump = 'OS|Mac OS X|10.6.8 10K549\nCPU|amd64|family 6 mod|1'
        comment0 = 'This is a comment\nOn multiple lines'
        comment0 += '\npeterbe@mozilla.com'
        comment0 += '\nwww.p0rn.com'

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(_SAMPLE_META)
                if params['datatype'] == 'unredacted':
                    return Response(dict(
                        _SAMPLE_UNREDACTED,
                        dump=dump,
                        user_comments=comment0
                    ))

            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        'FakeSignature1',
                        'FakeSignature2'
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

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
            .replace('peterbe@mozilla.com', '(email removed)')
            .replace('www.p0rn.com', '(URL removed)')
        )

        ok_(comment_transformed in response.content)
        # but the email should have been scrubbed
        ok_('peterbe@mozilla.com' not in response.content)
        ok_(_SAMPLE_META['Email'] not in response.content)
        ok_(_SAMPLE_META['URL'] not in response.content)
        ok_(
            'You need to be signed in to be able to download raw dumps.'
            in response.content
        )
        # Should not be able to see sensitive key from stackwalker JSON
        ok_('&#34;sensitive&#34;' not in response.content)
        ok_('&#34;exploitability&#34;' not in response.content)

        # should be a link there to crash analysis
        ok_(settings.CRASH_ANALYSIS_URL in response.content)

        # The pretty platform version should appear.
        ok_('OS X 10.11' in response.content)

        # the email address will appear if we log in
        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_pii')

        response = self.client.get(url)
        ok_('peterbe@mozilla.com' in response.content)
        ok_(_SAMPLE_META['Email'] in response.content)
        ok_(_SAMPLE_META['URL'] in response.content)
        ok_('&#34;sensitive&#34;' in response.content)
        ok_('&#34;exploitability&#34;' in response.content)
        eq_(response.status_code, 200)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_additional_raw_dump_links(self, rget, rpost):
        # using \\n because it goes into the JSON string
        dump = 'OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1'

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response({
                        'InstallTime': '1339289895',
                        'FramePoisonSize': '4096',
                        'Theme': 'classic/1.0',
                        'Version': '5.0a1',
                        'Email': 'secret@email.com',
                        'Vendor': 'Mozilla',
                        'URL': 'farmville.com',
                        'additional_minidumps': 'foo, bar,',
                    })
                if params['datatype'] == 'unredacted':
                    return Response({
                        'client_crash_date': '2012-06-11T06:08:45',
                        'dump': dump,
                        'signature': 'FakeSignature1',
                        'user_comments': None,
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
                        'last_crash': 371342,
                        'date_processed': '2012-06-11T06:08:44',
                        'cpu_name': 'amd64',
                        'reason': 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS',
                        'address': '0x8',
                        'completeddatetime': '2012-06-11T06:08:57',
                        'success': True,
                        'exploitability': 'Unknown Exploitability'
                    })

            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        'FakeSignature1',
                        'FakeSignature2'
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

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

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_symbol_url_in_modules(self, rget, rpost):
        rpost.side_effect = mocked_post_threeothersigs
        dump = 'OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1'
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

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response({
                        'InstallTime': '1339289895',
                        'FramePoisonSize': '4096',
                        'Theme': 'classic/1.0',
                        'Version': '5.0a1',
                        'Email': 'secret@email.com',
                        'Vendor': 'Mozilla',
                        'URL': 'farmville.com',
                        'additional_minidumps': 'foo, bar,',
                    })
                if params['datatype'] == 'unredacted':
                    return Response({
                        'client_crash_date': '2012-06-11T06:08:45',
                        # 'dump': 'OS|Mac OS X|10.6.8 10K549\nCPU|amd64',
                        'dump': dump,
                        'signature': 'FakeSignature1',
                        'user_comments': None,
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
                        'last_crash': 371342,
                        'date_processed': '2012-06-11T06:08:44',
                        'cpu_name': 'amd64',
                        'reason': 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS',
                        'address': '0x8',
                        'completeddatetime': '2012-06-11T06:08:57',
                        'success': True,
                        'exploitability': 'Unknown Exploitability',
                        'json_dump': json_dump,
                    })

            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        'FakeSignature1',
                        'FakeSignature2'
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        url = reverse('crashstats:report_index', args=(crash_id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        assert 'id="modules-list"' in response.content
        ok_(
            '<a href="https://s3.example.com/winmm.sym">winmm.dll</a>' in
            response.content
        )

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_fennecandroid_report(self, rget, rpost):
        dump = 'OS|Mac OS X|10.6.8 10K549\nCPU|amd64|family 6 mod|1'
        comment0 = 'This is a comment\nOn multiple lines'
        comment0 += '\npeterbe@mozilla.com'
        comment0 += '\nwww.p0rn.com'

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(_SAMPLE_META)
                if params['datatype'] == 'unredacted':
                    raw_crash = dict(
                        _SAMPLE_UNREDACTED,
                        dump=dump,
                        user_comments=comment0,
                    )
                    raw_crash['product'] = 'WinterSun'

                    return Response(raw_crash)

            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        'FakeSignature1',
                        'FakeSignature2'
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

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

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_odd_product_and_version(self, rget, rpost):
        """If the processed JSON references an unfamiliar product and
        version it should not use that to make links in the nav to
        reports for that unfamiliar product and version."""
        dump = 'OS|Mac OS X|10.6.8 10K549\nCPU|amd64|family 6 mod|1'
        comment0 = 'This is a comment\nOn multiple lines'
        comment0 += '\npeterbe@mozilla.com'
        comment0 += '\nwww.p0rn.com'

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(_SAMPLE_META)
                if params['datatype'] == 'unredacted':
                    processed = dict(
                        _SAMPLE_UNREDACTED,
                        dump=dump,
                        user_comments=comment0,
                    )
                    processed['product'] = 'SummerWolf'
                    processed['version'] = '99.9'
                    return Response(processed)

            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        'FakeSignature1',
                        'FakeSignature2'
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

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

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_correlations_failed(self, rget, rpost):
        dump = 'OS|Mac OS X|10.6.8 10K549\nCPU|amd64|family 6 mod|1'
        comment0 = 'This is a comment'

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(_SAMPLE_META)
                if params['datatype'] == 'unredacted':
                    return Response(dict(
                        _SAMPLE_UNREDACTED,
                        dump=dump,
                        user_comments=comment0,
                    ))

            if 'correlations/signatures' in url:
                raise models.BadStatusCodeError(500)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_no_dump(self, rget, rpost):
        dump = ''
        comment0 = 'This is a comment'

        rpost.side_effect = mocked_post_threesigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(_SAMPLE_META)
                if params['datatype'] == 'unredacted':
                    data = dict(
                        _SAMPLE_UNREDACTED,
                        dump=dump,
                        user_comments=comment0,
                    )
                    del data['dump']
                    del data['json_dump']
                    return Response(data)

            if 'correlations/signatures' in url:
                raise models.BadStatusCodeError(500)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

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

    @mock.patch('requests.get')
    def test_report_pending_today(self, rget):
        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                raise models.BadStatusCodeError(404)

        rget.side_effect = mocked_get

        today = datetime.datetime.utcnow().strftime('%y%m%d')
        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982%s' % today])
        response = self.client.get(url)
        ok_('pendingStatus' in response.content)
        eq_(response.status_code, 200)

        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        yesterday = yesterday.strftime('%y%m%d')
        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982%s' % yesterday])
        response = self.client.get(url)
        ok_('Crash Not Found' in response.content)
        eq_(response.status_code, 200)

        url = reverse('crashstats:report_index',
                      args=['blablabla'])
        response = self.client.get(url)
        eq_(response.status_code, 400)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_valid_install_time(self, rget, rpost):
        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response({
                    'InstallTime': '1461170304',
                    'Version': '5.0a1',
                })
            if 'crashes/comments' in url:
                return Response({
                    'hits': [],
                    'total': 0,
                })
            if 'correlations/signatures' in url:
                return Response({
                    'hits': [],
                    'total': 0,
                })

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response({
                    'dump': 'some dump',
                    'signature': 'FakeSignature1',
                    'uuid': '11cb72f5-eb28-41e1-a8e4-849982120611',
                    'process_type': None,
                    'os_name': 'Windows NT',
                    'product': 'WaterWolf',
                    'version': '1.0',
                    'cpu_name': 'amd64',
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse(
            'crashstats:report_index',
            args=['11cb72f5-eb28-41e1-a8e4-849982120611']
        )
        response = self.client.get(url)
        ok_('<th scope="row">Install Time</th>' in response.content)
        # This is what 1461170304 is in human friendly format.
        ok_('2016-04-20 16:38:24' in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_invalid_install_time(self, rget, rpost):

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response({
                    'InstallTime': 'Not a number',
                    'Version': '5.0a1',
                    'Email': '',
                    'URL': None,
                })
            if 'crashes/comments' in url:
                return Response({
                    'hits': [],
                    'total': 0,
                })
            if 'correlations/signatures' in url:
                return Response({
                    'hits': [],
                    'total': 0
                })

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response({
                    'dump': 'some dump',
                    'signature': 'FakeSignature1',
                    'uuid': '11cb72f5-eb28-41e1-a8e4-849982120611',
                    'process_type': None,
                    'os_name': 'Windows NT',
                    'product': 'WaterWolf',
                    'version': '1.0',
                    'cpu_name': 'amd64',
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse(
            'crashstats:report_index',
            args=['11cb72f5-eb28-41e1-a8e4-849982120611']
        )
        response = self.client.get(url)
        # The heading is there but there should not be a value for it
        ok_('<th scope="row">Install Time</th>' in response.content)
        doc = pyquery.PyQuery(response.content)
        # Look for a <tr> whose <th> is 'Install Time', then
        # when we've found the row, we look at the text of its <td> child.
        for row in doc('#details tr'):
            if pyquery.PyQuery(row).find('th').text() == 'Install Time':
                eq_(pyquery.PyQuery(row).find('td').text(), '')

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_known_total_correlations(self, rget, rpost):

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response({
                    'InstallTime': 'Not a number',
                    'Version': '5.0a1',
                    'Email': '',
                    'URL': None,
                })
            if 'crashes/comments' in url:
                return Response({
                    'hits': [],
                    'total': 0,
                })
            if 'correlations/signatures' in url:
                return Response({
                    'hits': [],
                    'total': 0
                })

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response({
                    'dump': 'some dump',
                    'signature': 'FakeSignature1',
                    'uuid': '11cb72f5-eb28-41e1-a8e4-849982120611',
                    'process_type': None,
                    'os_name': 'Windows NT',
                    'product': 'WaterWolf',
                    'version': '1.0',
                    'cpu_name': 'amd64',
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse(
            'crashstats:report_index',
            args=['11cb72f5-eb28-41e1-a8e4-849982120611']
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        for node in doc('#mainbody'):
            eq_(node.attrib['data-total-correlations'], '-1')

        # now, manually prime the cache so that this is set
        cache_key = views.make_correlations_count_cache_key(
            'WaterWolf',
            '1.0',
            'Windows NT',
            'FakeSignature1',
        )
        cache.set(cache_key, 123)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        for node in doc('#mainbody'):
            eq_(node.attrib['data-total-correlations'], '123')

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_empty_os_name(self, rget, rpost):

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response({
                    'InstallTime': 'Not a number',
                    'Version': '5.0a1',
                    'Email': '',
                    'URL': None,
                })
            if 'crashes/comments' in url:
                return Response({
                    'hits': [],
                    'total': 0,
                })
            if 'correlations/signatures' in url:
                return Response({
                    'hits': [],
                    'total': 0
                })

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response({
                    'dump': 'some dump',
                    'signature': 'FakeSignature1',
                    'uuid': '11cb72f5-eb28-41e1-a8e4-849982120611',
                    'process_type': None,
                    'os_name': None,
                    'product': 'WaterWolf',
                    'version': '1.0',
                    'cpu_name': 'amd64',
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

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

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_invalid_parsed_dump(self, rget, rpost):
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

        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"
        email1 = "some@otheremailaddress.com"

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response({
                    "InstallTime": "Not a number",
                    "FramePoisonSize": "4096",
                    "Theme": "classic/1.0",
                    "Version": "5.0a1",
                    "Email": email0,
                    "Vendor": "Mozilla",
                    "URL": url0,
                    "HangID": "123456789"
                })
            if 'crashes/comments' in url:
                return Response({
                    "hits": [
                        {
                            "user_comments": comment0,
                            "date_processed": "2012-08-21T11:17:28-07:00",
                            "email": email1,
                            "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                        }
                    ],
                    "total": 1
                })
            if 'correlations/signatures' in url:
                return Response({
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                })

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response({
                    "client_crash_date": "2012-06-11T06:08:45",
                    "json_dump": json_dump,
                    "signature": "FakeSignature1",
                    "user_comments": None,
                    "uptime": 14693,
                    "release_channel": "nightly",
                    "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                    "flash_version": "[blank]",
                    "hangid": None,
                    "distributor_version": None,
                    "truncated": True,
                    "process_type": None,
                    "id": 383569625,
                    "os_version": "10.6.8 10K549",
                    "version": "5.0a1",
                    "build": "20120609030536",
                    "ReleaseChannel": "nightly",
                    "addons_checked": None,
                    "product": "WaterWolf",
                    "os_name": "Mac OS X",
                    "last_crash": 371342,
                    "date_processed": "2012-06-11T06:08:44",
                    "cpu_name": "amd64",
                    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                    "address": "0x8",
                    "completeddatetime": "2012-06-11T06:08:57",
                    "success": True,
                    "exploitability": "Unknown Exploitability"
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        ok_('<th>Install Time</th>' not in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_sparse_json_dump(self, rget, rpost):
        json_dump = {'status': 'ERROR_NO_MINIDUMP_HEADER', 'sensitive': {}}

        comment0 = 'This is a comment'
        email0 = 'some@emailaddress.com'
        url0 = 'someaddress.com'
        email1 = 'some@otheremailaddress.com'

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response({
                    'InstallTime': 'Not a number',
                    'FramePoisonSize': '4096',
                    'Theme': 'classic/1.0',
                    'Version': '5.0a1',
                    'Email': email0,
                    'Vendor': 'Mozilla',
                    'URL': url0,
                    'HangID': '123456789',
                })
            if 'crashes/comments' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': comment0,
                            'date_processed': '2012-08-21T11:17:28-07:00',
                            'email': email1,
                            'uuid': '469bde48-0e8f-3586-d486-b98810120830',
                        }
                    ],
                    'total': 1
                })
            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        'FakeSignature1',
                        'FakeSignature2'
                    ],
                    'total': 2
                })

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response({
                    'client_crash_date': '2012-06-11T06:08:45',
                    'json_dump': json_dump,
                    'signature': 'FakeSignature1',
                    'user_comments': None,
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
                    'last_crash': 371342,
                    'date_processed': '2012-06-11T06:08:44',
                    'cpu_name': 'amd64',
                    'reason': 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS',
                    'address': '0x8',
                    'completeddatetime': '2012-06-11T06:08:57',
                    'success': True,
                    'exploitability': 'Unknown Exploitability'
                })

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_crash_exploitability(self, rget, rpost):
        dump = 'OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1'
        comment0 = 'This is a comment'
        email0 = 'some@emailaddress.com'
        url0 = 'someaddress.com'
        email1 = 'some@otheremailaddress.com'

        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response({
                    'InstallTime': 'Not a number',
                    'FramePoisonSize': '4096',
                    'Theme': 'classic/1.0',
                    'Version': '5.0a1',
                    'Email': email0,
                    'Vendor': 'Mozilla',
                    'URL': url0,
                    'HangID': '123456789',
                })
            if '/crashes/comments' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': comment0,
                            'date_processed': '2012-08-21T11:17:28-07:00',
                            'email': email1,
                            'uuid': '469bde48-0e8f-3586-d486-b98810120830',
                        }
                    ],
                    'total': 1
                })
            if '/correlations/signatures' in url:
                return Response({
                    'hits': [
                        'FakeSignature1',
                        'FakeSignature2',
                    ],
                    'total': 2
                })

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response({
                    'client_crash_date': '2012-06-11T06:08:45',
                    'dump': dump,
                    'signature': 'FakeSignature1',
                    'user_comments': None,
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
                    'last_crash': 371342,
                    'date_processed': '2012-06-11T06:08:44',
                    'cpu_name': 'amd64',
                    'reason': 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS',
                    'address': '0x8',
                    'completeddatetime': '2012-06-11T06:08:57',
                    'success': True,
                    'exploitability': 'Unknown Exploitability',
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

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

    @mock.patch('requests.get')
    def test_report_index_processed_crash_not_found(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                raise models.BadStatusCodeError(404)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_('Crash Not Found' in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_raw_crash_not_found(self, rget, rpost):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        dump = 'OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1'

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            assert '/crash_data/' in url
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                return Response({
                    'client_crash_date': '2012-06-11T06:08:45',
                    'dump': dump,
                    'signature': 'FakeSignature1',
                    'user_comments': None,
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
                    'last_crash': 371342,
                    'date_processed': '2012-06-11T06:08:44',
                    'cpu_name': 'amd64',
                    'reason': 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS',
                    'address': '0x8',
                    'completeddatetime': '2012-06-11T06:08:57',
                    'success': True,
                    'exploitability': 'Unknown Exploitability'
                })
            elif params['datatype'] == 'meta':  # raw crash json!
                raise models.BadStatusCodeError(404)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_('Crash Not Found' in response.content)

    @mock.patch('requests.get')
    def test_report_index_pending(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                raise models.BadStatusCodeError(408)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_('Fetching this archived report' in response.content)

    @mock.patch('requests.get')
    def test_report_index_too_old(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                raise models.BadStatusCodeError(410)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_('This archived report has expired' in response.content)

    @mock.patch('requests.get')
    def test_report_index_other_error(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response('Scary Error', status_code=500)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=[crash_id])
        assert_raises(
            models.BadStatusCodeError,
            self.client.get,
            url
        )
        # Let's also check that we get the response in the exception
        # message.
        try:
            self.client.get(url)
            assert False  # shouldn't get here
        except models.BadStatusCodeError as exception:
            ok_('Scary Error' in str(exception))
            # and it should include the URL it used
            mware_url = models.UnredactedCrash.base_url + '/crash_data/'
            ok_(mware_url in str(exception))

    @mock.patch('requests.get')
    def test_report_pending_json(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                raise models.BadStatusCodeError(408)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_pending',
                      args=[crash_id])
        response = self.client.get(url)

        expected = {
            'status': 'error',
            'status_message': ('The report for %s'
                               ' is not available yet.' % crash_id),
            'url_redirect': ''
        }

        eq_(response.status_code, 200)
        eq_(expected, json.loads(response.content))

    def test_report_index_and_pending_missing_crash_id(self):
        url = reverse('crashstats:report_index', args=[''])
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('crashstats:report_pending', args=[''])
        response = self.client.get(url)
        eq_(response.status_code, 404)

    def test_report_list(self):
        url = reverse('crashstats:report_list')
        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 'xxx'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {'signature': 'sig'})
        eq_(response.status_code, 200)

        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        ok_('Crash Reports for sig' in response.content)

    def test_report_list_all_link(self):
        url = reverse('crashstats:report_list')
        sig = 'js::jit::EnterBaselineMethod(JSContext*, js::RunState&)'
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'signature': sig
        })
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        for link in doc('a'):
            if link.text and 'View ALL' in link.text:
                ok_(urllib.quote(sig) in link.attrib['href'])

    def test_report_list_all_link_columns_offered(self):
        url = reverse('crashstats:report_list')
        response = self.client.get(url, {'signature': 'sig'})
        eq_(response.status_code, 200)
        # The "user_comments" field is a choice
        ok_('<option value="user_comments">' in response.content)
        # The "URL" field is not a choice
        ok_('<option value="URL">' not in response.content)

        # also, all fields in models.RawCrash.API_WHITELIST should
        # be there
        for field in models.RawCrash.API_WHITELIST:
            html = '<option value="%s">' % field
            ok_(html in response.content)

        # but it's different if you're logged in
        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)
        response = self.client.get(url, {'signature': 'sig'})
        eq_(response.status_code, 200)
        ok_('<option value="user_comments">' in response.content)
        ok_('<option value="URL">' in response.content)
        # and a column from the Raw Crash
        ok_('<option value="Accessibility">' in response.content)
        # and it's only supposed to appear once
        eq_(response.content.count('<option value="Accessibility">'), 1)

    @mock.patch('requests.get')
    def test_report_list_partial_correlations(self, rget):

        def mocked_get(url, params, **options):
            if 'report/list' in url:
                # Note that the key `install_time` was removed from the
                # second dict here. The reason for that is the install_time
                # is not a depdendable field from the breakpad client.
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Linux',
                            'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/116',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'release_channel': 'Release',
                            'process_type': 'browser',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '19.0',
                            'os_version': '1.2.3.4',
                            'build': '20120901000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:0',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        },
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Mac OS X',
                            'uuid': 'e491c551-be0d-b0fb-c69e-107380120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/60053',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'release_channel': 'Release',
                            'process_type': 'content',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '19.0',
                            'os_version': '1.2.3.4',
                            'build': '20120822000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        }
                    ],
                    'total': 2
                })
            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Linux',
                            'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/116',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'release_channel': 'Release',
                            'process_type': 'browser',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '19.0',
                            'os_version': '1.2.3.4',
                            'build': '20120901000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        },
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Mac OS X',
                            'uuid': 'e491c551-be0d-b0fb-c69e-107380120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/60053',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'release_channel': 'Release',
                            'process_type': 'content',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '19.0',
                            'os_version': '1.2.3.4',
                            'build': '20120822000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:0',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        }
                    ],
                    'total': 2
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('correlations',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        # relevant data is put into 'data' attributes
        doc = pyquery.PyQuery(response.content)
        combos = doc('.correlation-combo')
        eq_(combos.size(), settings.MAX_CORRELATION_COMBOS_PER_SIGNATURE)
        first, = combos[:1]
        eq_(first.attrib['data-correlation-product'], 'WaterWolf')
        eq_(first.attrib['data-correlation-version'], '19.0')
        eq_(first.attrib['data-correlation-os'], 'Mac OS X')

    @mock.patch('requests.get')
    def test_report_list_partial_correlations_no_data(self, rget):
        """This time, in the fixture we return a version (0.1) which
        is NOT one of the known releases (18.0, 19.0, 20.0) for WaterWolf.
        """

        def mocked_get(url, params, **options):
            if 'report/list' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Mac OS X',
                            'uuid': 'e491c551-be0d-b0fb-c69e-107380120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/60053',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'release_channel': 'Release',
                            'process_type': 'content',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '0.1',
                            'os_version': '1.2.3.4',
                            'build': '20120822000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:0',
                            'address': '0xdeadbeef',
                            'duplicate_of': None,
                        }
                    ],
                    'total': 1
                })
            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Linux',
                            'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/116',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'release_channel': 'Release',
                            'process_type': 'browser',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '0.1',
                            'os_version': '1.2.3.4',
                            'build': '20120901000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        },
                    ],
                    'total': 1
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('correlations',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        combos = doc('.correlation-combo')
        eq_(combos.size(), 0)
        ok_(
            'No product &amp; version &amp; OS combination for all reports '
            'under this signature' in response.content
        )

    @mock.patch('requests.get')
    def test_report_list_partial_sigurls(self, rget):

        def mocked_get(url, params, **options):
            # no specific product was specified, then it should be all products
            ok_('products' in params)
            ok_(settings.DEFAULT_PRODUCT not in params['products'])
            ok_('ALL' in params['products'])

            if '/signatureurls' in url:
                return Response({
                    'hits': [
                        {'url': 'http://farm.ville', 'crash_count': 123}
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('sigurls',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        ok_('Must be signed in to see signature URLs' in response.content)
        ok_('http://farm.ville' not in response.content)

        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        eq_(response.content.count('http://farm.ville'), 3)

    @mock.patch('requests.get')
    def test_report_list_partial_sigurls_specific_product(self, rget):

        really_long_url = (
            'http://thisistheworldsfivehundredthirtyfifthslong'
            'esturk.com/that/contains/a/path/and/?a=query&'
        )
        assert len(really_long_url) > 80

        def mocked_get(url, params, **options):
            # 'NightTrain' was specifically requested
            ok_('products' in params)
            ok_('NightTrain' in params['products'])

            if '/signatureurls' in url:
                return Response({
                    'hits': [
                        {'url': 'http://farm.ville', 'crash_count': 123},
                        {'url': really_long_url, 'crash_count': 1},
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)

        url = reverse('crashstats:report_list_partial', args=('sigurls',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3,
            'product': 'NightTrain'
        })
        eq_(response.status_code, 200)
        eq_(response.content.count('http://farm.ville'), 3)

    @mock.patch('requests.get')
    def test_report_list_partial_comments(self, rget):

        def mocked_get(url, params, **options):
            if '/crashes/comments' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': 'I LOVE CHEESE cheese@email.com',
                            'date_processed': '2012-08-21T11:17:28-07:00',
                            'email': 'bob@uncle.com',
                            'uuid': '469bde48-0e8f-3586-d486-b98810120830'
                        }
                    ],
                    'total': 1
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('comments',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        ok_('I LOVE CHEESE' in response.content)
        ok_('email removed' in response.content)
        ok_('bob@uncle.com' not in response.content)
        ok_('cheese@email.com' not in response.content)

        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        ok_('I LOVE CHEESE' in response.content)
        ok_('email removed' not in response.content)
        ok_('bob@uncle.com' in response.content)
        ok_('cheese@email.com' in response.content)

    @mock.patch('requests.get')
    def test_report_list_partial_comments_paginated(self, rget):

        called_with_params = []

        def mocked_get(url, params, **options):
            if '/crashes/comments' in url:
                called_with_params.append(params)
                if params.get('result_offset'):
                    return Response({
                        'hits': [{
                            'user_comments': 'I LOVE HAM',
                            'date_processed': '2012-08-21T11:17:28-07:00',
                            'email': 'bob@uncle.com',
                            'uuid': '469bde48-0e8f-3586-d486-b98810120830'
                        }],
                        'total': 2
                    })
                else:
                    return Response({
                        'hits': [{
                            'user_comments': 'I LOVE CHEESE',
                            'date_processed': '2011-08-21T11:17:28-07:00',
                            'email': 'bob@uncle.com',
                            'uuid': '469bde48-0e8f-3586-d486-b98810120829'
                        }],
                        'total': 2
                    })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('comments',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        ok_('I LOVE CHEESE' in response.content)
        ok_('I LOVE HAM' not in response.content)

        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3,
            'page': 2,
        })
        eq_(response.status_code, 200)
        ok_('I LOVE HAM' in response.content)
        ok_('I LOVE CHEESE' not in response.content)

        eq_(len(called_with_params), 2)

    @mock.patch('requests.get')
    def test_report_list_partial_reports(self, rget):

        def mocked_get(url, params, **options):
            if 'report/list' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Linux',
                            'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/116',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'browser',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120901000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None,
                        },
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Mac OS X',
                            'uuid': 'e491c551-be0d-b0fb-c69e-107380120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/60053',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'content',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120822000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None,
                        }
                    ],
                    'total': 2
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('reports',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        ok_('0xdeadbeef' in response.content)

    @mock.patch('requests.get')
    def test_report_list_partial_reports_with_sorting(self, rget):

        mock_calls = []

        def mocked_get(url, params, **options):
            mock_calls.append(params)

            if 'report/list' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Linux',
                            'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/116',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'browser',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120901000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        },
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Mac OS X',
                            'uuid': 'e491c551-be0d-b0fb-c69e-107380120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/60053',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T22:19:59+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'content',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120822000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        }
                    ],
                    'total': 2
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('reports',))
        data = {
            'signature': 'FakeSignature2',
            'range_value': 3
        }
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        assert len(mock_calls) == 1
        eq_(mock_calls[-1]['sort'], 'date_processed')
        eq_(mock_calls[-1]['reverse'], True)

        response = self.client.get(url, dict(
            data,
            sort='build'
        ))
        eq_(response.status_code, 200)
        assert len(mock_calls) == 2
        eq_(mock_calls[-1]['sort'], 'build')
        eq_(mock_calls[-1]['reverse'], True)

        response = self.client.get(url, dict(
            data,
            sort='build',
            reverse='False'
        ))
        eq_(response.status_code, 200)
        assert len(mock_calls) == 3
        eq_(mock_calls[-1]['sort'], 'build')
        eq_(mock_calls[-1]['reverse'], False)

    @mock.patch('requests.get')
    def test_report_list_partial_reports_columns_override(self, rget):

        def mocked_get(url, params, **options):
            if 'report/list' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Linux',
                            'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/116',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'browser',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120901000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        },
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Mac OS X',
                            'uuid': 'e491c551-be0d-b0fb-c69e-107380120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/60053',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'content',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120822000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        }
                    ],
                    'total': 2
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('reports',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3,
            'c': ['crap', 'date_processed', 'reason', 'os_and_version']
        })
        eq_(response.status_code, 200)
        # 'reason' in _columns
        ok_('reason7' in response.content)
        # 'address' not in _columns
        ok_('0xdeadbeef' not in response.content)
        # 'cpu_name' not in _columns
        ok_('x86' not in response.content)
        # 'os_and_version' not in _columns
        ok_('Mac OS X' in response.content)

    @mock.patch('requests.get')
    def test_report_list_partial_reports_with_rawcrash(self, rget):

        def mocked_get(url, params, **options):
            if 'report/list' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Linux',
                            'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/116',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'browser',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120901000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None,
                            'raw_crash': {
                                'Winsock_LSP': 'Peter',
                                'SecondsSinceLastCrash': 'Bengtsson',
                            },
                        },
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Mac OS X',
                            'uuid': 'e491c551-be0d-b0fb-c69e-107380120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/60053',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'content',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120822000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None,
                            'raw_crash': None,
                        },
                    ],
                    'total': 2
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('reports',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3,
            'c': ['date_processed', 'Winsock_LSP', 'SecondsSinceLastCrash']
        })
        eq_(response.status_code, 200)
        ok_('Peter' in response.content)
        ok_('Bengtsson' in response.content)
        # and also the table headers should be there
        ok_('Winsock_LSP*' in response.content)
        ok_('SecondsSinceLastCrash*' in response.content)

    @mock.patch('requests.get')
    def test_report_list_partial_reports_page_2(self, rget):

        uuids = []
        _date = datetime.datetime.now()
        for i in range(300):
            uuids.append(
                '441017f4-e006-4eea-8451-dc20e' +
                _date.strftime('%Y%m%d')
            )
            _date += datetime.timedelta(days=1)

        def mocked_get(url, params, **options):

            if 'report/list' in url:
                result_number = int(params['result_number'])
                try:
                    result_offset = int(params['result_offset'])
                except KeyError:
                    result_offset = 0

                first = {
                    'user_comments': None,
                    'product': 'WaterWolf',
                    'os_name': 'Linux',
                    'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                    'cpu_info': '...',
                    'url': 'http://example.com/116',
                    'last_crash': 1234,
                    'date_processed': '2012-09-05T21:18:58+00:00',
                    'cpu_name': 'x86',
                    'uptime': 1234,
                    'process_type': 'browser',
                    'hangid': None,
                    'reason': 'reason7',
                    'version': '5.0a1',
                    'os_version': '1.2.3.4',
                    'build': '20120901000007',
                    'install_age': 1234,
                    'signature': 'FakeSignature',
                    'install_time': '2012-09-05T20:58:24+00:00',
                    'address': '0xdeadbeef',
                    'duplicate_of': None
                }
                hits = []

                for i in range(result_offset, result_offset + result_number):
                    try:
                        item = dict(first, uuid=uuids[i])
                        hits.append(item)
                    except IndexError:
                        break

                return Response({
                    'hits': hits,
                    'total': len(uuids)
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('reports',))
        response = self.client.get(url, {
            'signature': 'sig',
        })
        eq_(response.status_code, 200)
        ok_(uuids[0] in response.content)
        ok_(uuids[-1] not in response.content)
        # expect there to be a link with `page=2` in there
        report_list_url = reverse('crashstats:report_list')
        report_list_url += '?signature=sig'
        ok_(report_list_url + '&amp;page=2' in response.content)

        # we'll need a copy of this for later
        response_first = response

        response = self.client.get(url, {
            'signature': 'sig',
            'page': 2
        })
        eq_(response.status_code, 200)
        ok_(uuids[0] not in response.content)
        ok_(uuids[-1] in response.content)

        # try to be a smartass
        response_zero = self.client.get(url, {
            'signature': 'sig',
            'page': 0
        })
        eq_(response.status_code, 200)
        # because with page < 1 you get page=1
        tbody_zero = response_zero.content.split('<tbody')[1]
        tbody_first = response_first.content.split('<tbody')[1]
        eq_(hash(tbody_zero), hash(tbody_first))

        response = self.client.get(url, {
            'signature': 'sig',
            'page': 'xx'
        })
        eq_(response.status_code, 400)

    @mock.patch('requests.get')
    def test_report_list_partial_reports_non_defaults(self, rget):

        def mocked_get(url, params, **options):

            if 'report/list' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Linux',
                            'uuid': '441017f4-e006-4eea-8451-dc20e0120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/116',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'browser',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120901000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        },
                        {
                            'user_comments': None,
                            'product': 'WaterWolf',
                            'os_name': 'Mac OS X',
                            'uuid': 'e491c551-be0d-b0fb-c69e-107380120905',
                            'cpu_info': '...',
                            'url': 'http://example.com/60053',
                            'last_crash': 1234,
                            'date_processed': '2012-09-05T21:18:58+00:00',
                            'cpu_name': 'x86',
                            'uptime': 1234,
                            'process_type': 'content',
                            'hangid': None,
                            'reason': 'reason7',
                            'version': '5.0a1',
                            'os_version': '1.2.3.4',
                            'build': '20120822000007',
                            'install_age': 1234,
                            'signature': 'FakeSignature2',
                            'install_time': '2012-09-05T20:58:24+00:00',
                            'address': '0xdeadbeef',
                            'duplicate_of': None
                        }
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('reports',))
        data = {
            'signature': 'sig',
            'range_unit': settings.RANGE_UNITS[-1],
            'process_type': settings.PROCESS_TYPES[-1],
            'range_value': 48,
            'plugin_field': settings.PLUGIN_FIELDS[-1],
            'hang_type': settings.HANG_TYPES[-1],
            'plugin_query_type': settings.QUERY_TYPES[-1],
            'product': 'NightTrain',
        }
        response = self.client.get(url, data)
        eq_(response.status_code, 200)

    def test_report_list_partial_reports_invalid_range_value(self):
        url = reverse('crashstats:report_list_partial', args=('reports',))
        data = {
            'signature': 'sig',
            'range_unit': 'days',
            'process_type': settings.PROCESS_TYPES[-1],
            'range_value': 48,
            'plugin_field': settings.PLUGIN_FIELDS[-1],
            'hang_type': settings.HANG_TYPES[-1],
            'plugin_query_type': settings.QUERY_TYPES[-1],
            'product': 'NightTrain',
        }
        response = self.client.get(url, data)
        eq_(response.status_code, 400)

        response = self.client.get(url, dict(data, range_unit='weeks'))
        eq_(response.status_code, 400)

        response = self.client.get(url, dict(
            data,
            range_unit='hours',
            range_value=24 * 48
        ))
        eq_(response.status_code, 400)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    def test_report_list_partial_bugzilla(self, rpost):

        def mocked_post(**options):
            return {
                'hits': [
                    {'id': 111111,
                     'signature': 'Something'},
                    {'id': 123456789,
                     'signature': 'Something'}
                ]
            }
        rpost.side_effect = mocked_post

        url = reverse('crashstats:report_list_partial', args=('bugzilla',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        # not the right signature so it's part of "Related Crash Signatures"
        ok_(
            response.content.find('Related Crash Signatures') <
            response.content.find('123456789')
        )

        response = self.client.get(url, {
            'signature': 'Something',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        # now the right signature
        ok_('123456789' in response.content)
        ok_('111111' in response.content)

        # because bug id 123456789 is > than 111111 we expect that order
        # in the rendered output
        ok_(
            response.content.find('123456789') <
            response.content.find('111111') <
            response.content.find('Related Crash Signatures')
        )

    @mock.patch('requests.get')
    def test_report_list_partial_table(self, rget):

        def mocked_get(url, params, **options):

            if '/crashes/frequency' in url:
                # these fixtures make sure we stress the possibility that
                # the build_date might be invalid or simply just null.
                return Response({
                    'hits': [
                        {
                            'count': 1050,
                            'build_date': '20130806030203',
                            'count_mac': 0,
                            'frequency_windows': 1.0,
                            'count_windows': 1050,
                            'frequency': 1.0,
                            'count_linux': 0,
                            'total': 1050,
                            'frequency_linux': 0.0,
                            'frequency_mac': 0.0
                        },
                        {
                            'count': 1150,
                            'build_date': 'notadate',
                            'count_mac': 0,
                            'frequency_windows': 1.0,
                            'count_windows': 1150,
                            'frequency': 1.0,
                            'count_linux': 0,
                            'total': 1150,
                            'frequency_linux': 0.0,
                            'frequency_mac': 0.0
                        },
                        {
                            'count': 1250,
                            'build_date': None,
                            'count_mac': 0,
                            'frequency_windows': 1.0,
                            'count_windows': 1250,
                            'frequency': 1.0,
                            'count_linux': 0,
                            'total': 1250,
                            'frequency_linux': 0.0,
                            'frequency_mac': 0.0
                        },
                    ]
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('table',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        ok_('1050 - 100.0%' in response.content)
        ok_('1150 - 100.0%' in response.content)
        ok_('1250 - 100.0%' in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_redirect_by_prefix(self, rget, rpost):

        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1"
        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"
        email1 = "some@otheremailaddress.com"

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response({
                    'InstallTime': '1339289895',
                    'FramePoisonSize': '4096',
                    'Theme': 'classic/1.0',
                    'Version': '5.0a1',
                    'Email': email0,
                    'Vendor': 'Mozilla',
                    'URL': url0
                })
            if 'crashes/comments' in url:
                return Response({
                    'hits': [
                        {
                            'user_comments': comment0,
                            'date_processed': '2012-08-21T11:17:28-07:00',
                            'email': email1,
                            'uuid': '469bde48-0e8f-3586-d486-b98810120830'
                        }
                    ],
                    'total': 1
                })

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response({
                    'client_crash_date': '2012-06-11T06:08:45',
                    'dump': dump,
                    'signature': 'FakeSignature1',
                    'user_comments': None,
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
                    'last_crash': 371342,
                    'date_processed': '2012-06-11T06:08:44',
                    'cpu_name': 'amd64',
                    'reason': 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS',
                    'address': '0x8',
                    'completeddatetime': '2012-06-11T06:08:57',
                    'success': True,
                    'exploitability': 'Unknown Exploitability'
                })

            if 'correlations/signatures' in url:
                return Response({
                    'hits': [
                        'FakeSignature1',
                        'FakeSignature2',
                    ],
                    'total': 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        base_crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        crash_id = settings.CRASH_ID_PREFIX + base_crash_id
        assert len(crash_id) > 36
        url = reverse('crashstats:report_index', args=[crash_id])
        response = self.client.get(url)
        correct_url = reverse('crashstats:report_index', args=[base_crash_id])
        self.assertRedirects(response, correct_url)

    @mock.patch('requests.get')
    def test_report_list_with_no_data(self, rget):

        def mocked_get(url, params, **options):
            if 'report/list' in url:
                return Response({
                    'hits': [],
                    'total': 0
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('reports',))
        response = self.client.get(url, {'signature': 'sig'})
        eq_(response.status_code, 200)
        # it sucks to depend on the output like this but it'll do for now since
        # it's quite a rare occurance.
        ok_('</html>' not in response.content)  # it's a partial
        ok_('no reports in the time period specified' in response.content)

    @mock.patch('requests.get')
    def test_raw_data(self, rget):
        def mocked_get(url, params, **options):
            assert '/crash_data' in url
            if 'datatype' in params and params['datatype'] == 'raw':
                return Response("""
                  bla bla bla
                """.strip())
            else:
                # default is datatype/meta
                return Response({
                    'foo': 'bar',
                    'stuff': 123,
                })

        rget.side_effect = mocked_get

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
        def different_mocked_get(url, **options):
            if '/crash_data' in url and 'datatype=raw' in url:
                return Response("""
                  SOMETHING DIFFERENT
                """.strip())
            raise NotImplementedError(url)

        rget.side_effect = different_mocked_get

        response = self.client.get(dump_url)
        eq_(response.status_code, 200)
        ok_('bla bla bla' in response.content)  # still. good.

    @mock.patch('requests.get')
    def test_correlations_json(self, rget):
        url = reverse('crashstats:correlations_json')

        def mocked_get(url, params, **options):
            if '/correlations/' in url:
                ok_('report_type' in params)
                eq_(params['report_type'], 'core-counts')

                return Response({
                    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                    "count": 13,
                    "load": "36% (4/11) vs.  26% (47/180) amd64 with 2 cores"
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(
            url,
            {'correlation_report_types': ['core-counts'],
             'product': 'WaterWolf',
             'version': '19.0',
             'platform': 'Windows NT',
             'signature': 'FakeSignature'}
        )

        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        eq_(
            struct['core-counts']['reason'],
            'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS'
        )

    @mock.patch('requests.get')
    def test_correlations_count_json(self, rget):
        url = reverse('crashstats:correlations_count_json')

        correlation_get_report_types = []

        def mocked_get(url, params, **options):
            correlation_get_report_types.append(params['report_type'])
            if '/correlations/signatures/' in url:
                return Response({
                    'hits': ['FakeSignature1',
                             'FakeSignature2'],
                    'total': 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(
            url,
            {
                'product': 'WaterWolf',
                'version': '19.0',
                'platform': 'Junk',  # note!
                'signature': 'FakeSignature'
            }
        )
        eq_(response.status_code, 400)

        response = self.client.get(
            url,
            {
                'product': 'WaterWolf',
                'version': '19.0',
                'platform': 'Windows NT',
                'signature': 'FakeSignature'
            }
        )
        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        eq_(struct['count'], 0)

        response = self.client.get(
            url,
            {
                'product': 'WaterWolf',
                'version': '19.0',
                'platform': 'Windows NT',
                'signature': 'FakeSignature1'
            }
        )
        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        eq_(struct['count'], 5)

        # Having run this, we should now have that count cached
        cache_key = views.make_correlations_count_cache_key(
            'WaterWolf',
            '19.0',
            'Windows NT',
            'FakeSignature1'
        )
        cached = cache.get(cache_key)
        eq_(cached, 5)

    @mock.patch('requests.get')
    def test_correlations_signatures_json(self, rget):
        url = reverse('crashstats:correlations_signatures_json')

        def mocked_get(url, params, **options):
            if '/correlations/' in url:
                return Response({
                    'hits': ['FakeSignature1',
                             'FakeSignature2'],
                    'total': 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(
            url,
            {'correlation_report_types': ['core-counts'],
             'product': 'WaterWolf',
             'version': '19.0',
             'platforms': 'Windows NT,Linux'}
        )
        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        eq_(struct['core-counts']['total'], 2)

    def test_unauthenticated_user_redirected_from_protected_page(self):
        url = reverse(
            'crashstats:exploitable_crashes',
            args=(settings.DEFAULT_PRODUCT,)
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

    def test_make_correlations_count_cache_key(self):
        cache_key = views.make_correlations_count_cache_key(
            'Firefox',
            '1.0',
            'Windows',
            u'Some 💔 Unicode'
        )
        eq_(cache_key, 'total_correlations-6b300d846cd52316f6107e4522864b6e')
