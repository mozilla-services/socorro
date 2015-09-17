import copy
import csv
import datetime
import json
import mock
import re
import urllib

import pyquery

from cStringIO import StringIO
from nose.tools import eq_, ok_, assert_raises
from nose.plugins.skip import SkipTest
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
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
from crashstats.supersearch.models import SuperSearchFields, SuperSearch
from .test_models import Response


SAMPLE_STATUS = {
    "breakpad_revision": "1035",
    "hits": [
        {
            "date_oldest_job_queued": "2012-09-28T20:39:33+00:00",
            "date_recently_completed": "2012-09-28T20:40:00+00:00",
            "processors_count": 1,
            "avg_wait_sec": 16.407,
            "waiting_job_count": 56,
            "date_created": "2012-09-28T20:40:02+00:00",
            "id": 410655,
            "avg_process_sec": 0.914149
        },
        {
            "date_oldest_job_queued": "2012-09-28T20:34:33+00:00",
            "date_recently_completed": "2012-09-28T20:35:00+00:00",
            "processors_count": 1,
            "avg_wait_sec": 13.8293,
            "waiting_job_count": 48,
            "date_created": "2012-09-28T20:35:01+00:00",
            "id": 410654,
            "avg_process_sec": 1.24177
        },
        {
            "date_oldest_job_queued": "2012-09-28T20:29:32+00:00",
            "date_recently_completed": "2012-09-28T20:30:01+00:00",
            "processors_count": 1,
            "avg_wait_sec": 14.8803,
            "waiting_job_count": 1,
            "date_created": "2012-09-28T20:30:01+00:00",
            "id": 410653,
            "avg_process_sec": 1.19637
        }
    ],
    "total": 12,
    "socorro_revision": "017d7b3f7042ce76bc80949ae55b41d1e915ab62",
    "schema_revision": "schema_12345"
}

SAMPLE_META = """ {
    "InstallTime": "1339289895",
    "FramePoisonSize": "4096",
    "Theme": "classic/1.0",
    "Version": "5.0a1",
    "Email": "%s",
    "Vendor": "Mozilla",
    "URL": "%s"
} """

SAMPLE_UNREDACTED = """ {
    "client_crash_date": "2012-06-11T06:08:45",
    "dump": "%s",
    "signature": "FakeSignature1",
    "user_comments": "%s",
    "uptime": 14693,
    "release_channel": "nightly",
    "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
    "flash_version": "[blank]",
    "hangid": null,
    "distributor_version": null,
    "truncated": true,
    "process_type": null,
    "id": 383569625,
    "os_version": "10.6.8 10K549",
    "version": "5.0a1",
    "build": "20120609030536",
    "ReleaseChannel": "nightly",
    "addons_checked": null,
    "product": "WaterWolf",
    "os_name": "Mac OS X",
    "last_crash": 371342,
    "date_processed": "2012-06-11T06:08:44",
    "cpu_name": "amd64",
    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
    "address": "0x8",
    "completeddatetime": "2012-06-11T06:08:57",
    "success": true,
    "json_dump": {
      "status": "OK",
      "sensitive": {
        "exploitability": "high"
      },
      "threads": []
    }
} """

BUG_STATUS = {
    "hits": [
        {"id": "222222", "signature": "FakeSignature1"},
        {"id": "333333", "signature": "FakeSignature1"},
        {"id": "444444", "signature": "Other FakeSignature"}
    ]
}

SAMPLE_SIGNATURE_SUMMARY = {
    "reports": {
        "products": [
            {
                "version_string": "33.0a2",
                "percentage": "57.542",
                "report_count": 103,
                "product_name": "Firefox"
            },
        ],
        "uptime": [
            {
                "category": "< 1 min",
                "percentage": "29.126",
                "report_count": 30
            }
        ],
        "architecture": [
            {
                "category": "x86",
                "percentage": "100.000",
                "report_count": 103
            }
        ],
        "flash_version": [
            {
                "category": "[blank]",
                "percentage": "100.000",
                "report_count": 103
            }
        ],
        "graphics": [
            {
                "report_count": 24,
                "adapter_name": None,
                "vendor_hex": "0x8086",
                "percentage": "23.301",
                "vendor_name": None,
                "adapter_hex": "0x0166"
            }
        ],
        "distinct_install": [
            {
                "crashes": 103,
                "version_string": "33.0a2",
                "product_name": "Firefox",
                "installations": 59
            }
        ],
        "devices": [
            {
                "cpu_abi": "XXX",
                "manufacturer": "YYY",
                "model": "ZZZ",
                "version": "1.2.3",
                "report_count": 52311,
                "percentage": "48.440",
            }
        ],
        "os": [
            {
                "category": "Windows 8.1",
                "percentage": "55.340",
                "report_count": 57
            }
        ],
        "process_type": [
            {
                "category": "Browser",
                "percentage": "100.000",
                "report_count": 103
            }
        ],
        "exploitability": [
            {
                "low_count": 0,
                "high_count": 0,
                "null_count": 0,
                "none_count": 4,
                "report_date": "2014-08-12",
                "medium_count": 0
            }
        ]
    }
}


# Helper mocks for several tests
def mocked_post_123(**options):
    return {
        "hits": [{
            "id": "123456789",
            "signature": "Something"
        }]
    }


def mocked_post_threesigs(**options):
    return {
        "hits": [
            {"id": "111111111", "signature": "FakeSignature 1"},
            {"id": "222222222", "signature": "FakeSignature 3"},
            {"id": "101010101", "signature": "FakeSignature"}
        ]
    }


def mocked_post_nohits(**options):
    return {"hits": [], "total": 0}


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

        # we do this here so that the current/versions thing
        # is cached since that's going to be called later
        # in every view more or less
        def mocked_get(url, params, **options):
            now = datetime.datetime.utcnow()
            yesterday = now - datetime.timedelta(days=1)
            if '/platforms/' in url:
                return Response({
                    "hits": [
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
                    "total": 6
                })
            if 'products/' in url:
                return Response("""
                    {"products": [
                       "WaterWolf",
                       "NightTrain",
                       "SeaMonkey",
                       "LandCrab"
                     ],
                     "hits": {
                      "WaterWolf": [
                       {"product": "WaterWolf",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08",
                        "featured": true,
                        "version": "19.0",
                        "release": "Beta",
                        "id": 922},
                       {"product": "WaterWolf",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08",
                        "featured": true,
                        "version": "18.0",
                        "release": "Stable",
                        "id": 920},
                       {"product": "WaterWolf",
                        "throttle": "100.00",
                        "end_date": "2012-03-09",
                        "start_date": "2012-03-08",
                        "featured": true,
                        "version": "19.1",
                        "release": "Nightly",
                        "id": 928},
                       {"product": "WaterWolf",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08",
                        "featured": true,
                        "version": "20.0",
                        "release": "Nightly",
                        "id": 923}
                      ],
                      "NightTrain":[
                        {"product": "NightTrain",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08",
                        "featured": true,
                        "version": "18.0",
                        "release": "Aurora",
                        "id": 924},
                       {"product": "NightTrain",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08",
                        "featured": true,
                        "version": "19.0",
                        "release": "Nightly",
                        "id": 925}
                     ],
                     "SeaMonkey": [
                       {"product": "SeaMonkey",
                        "throttle": "99.00",
                        "end_date": "%(yesterday)s",
                        "start_date": "2012-03-08",
                        "featured": true,
                        "version": "9.5",
                        "release": "Alpha",
                        "id": 921},
                        {"product": "SeaMonkey",
                        "throttle": "99.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08",
                        "featured": true,
                        "version": "10.5",
                        "release": "nightly",
                        "id": 926}
                     ],
                     "LandCrab": [
                        {"product": "LandCrab",
                        "throttle": "99.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08",
                        "featured": false,
                        "version": "1.5",
                        "release": "Release",
                        "id": 927}
                     ]
                   },
                   "total": 4
                 }
                      """ % {'end_date': now.strftime('%Y-%m-%d'),
                             'yesterday': yesterday.strftime('%Y-%m-%d')})
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

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
        from crashstats.crashstats.models import CurrentVersions, Platforms
        CurrentVersions().get()
        Platforms().get()

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
    @mock.patch('requests.get')
    def test_google_analytics(self, rget):
        url = reverse('crashstats:home', args=('WaterWolf',))

        def mocked_get(url, params, **options):
            if 'products' in url:
                return Response("""
                    {
                        "hits": [{
                            "is_featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "WaterWolf",
                            "build_type": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                        }],
                        "total": 1
                    }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('xyz123' in response.content)
        ok_('test.biz' in response.content)

    @override_settings(PINGDOM_RUM_ID='abc123')
    @mock.patch('requests.get')
    def test_pingdom_rum(self, rget):
        url = reverse('crashstats:home', args=('WaterWolf',))

        def mocked_get(url, params, **options):
            if 'products' in url:
                return Response("""
                    {
                        "hits": [{
                            "is_featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "WaterWolf",
                            "build_type": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                        }],
                        "total": 1
                    }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('abc123' in response.content)
        ok_('pingdom.net/prum.min.js' in response.content)


class TestViews(BaseTestViews):

    def test_contribute_json(self):
        response = self.client.get('/contribute.json')
        eq_(response.status_code, 200)
        # Should be valid JSON, but it's a streaming content because
        # it comes from django.views.static.serve
        ok_(json.loads(''.join(response.streaming_content)))
        eq_(response['Content-Type'], 'application/json')

    @mock.patch('requests.get')
    def test_handler500(self, rget):
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

    def test_handler404(self):
        url = reverse('crashstats:home', args=('Unknown',))
        response = self.client.get(url)
        eq_(response.status_code, 404)
        ok_('Page not Found' in response.content)
        ok_('id="products_select"' not in response.content)

    def test_homepage_redirect(self):
        response = self.client.get('/')
        eq_(response.status_code, 302)
        destination = reverse('crashstats:home',
                              args=[settings.DEFAULT_PRODUCT])
        ok_(destination in response['Location'])

    def test_homepage_products_redirect_without_versions(self):
        url = reverse('crashstats:home', args=['WaterWolf'])
        # some legacy URLs have this
        url += '/versions/'
        response = self.client.get(url)
        redirect_code = settings.PERMANENT_LEGACY_REDIRECTS and 301 or 302
        eq_(response.status_code, redirect_code)
        destination = reverse('crashstats:home', args=['WaterWolf'])
        ok_(destination in response['Location'])

    @mock.patch('requests.get')
    def test_buginfo(self, rget):
        url = reverse('crashstats:buginfo')

        def mocked_get(url, params, **options):
            if 'bug?id=' in url:
                return Response('{"bugs": [{"product": "allizom.org"}]}')

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_ids': '123,456'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'include_fields': 'product'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_ids': ' 123, 456 ',
                                         'include_fields': ' product'})
        eq_(response.status_code, 200)

        struct = json.loads(response.content)
        ok_(struct['bugs'])
        eq_(struct['bugs'][0]['product'], 'allizom.org')

    @mock.patch('requests.get')
    def test_buginfo_with_caching(self, rget):
        url = reverse('crashstats:buginfo')

        def mocked_get(url, params, **options):
            if 'bug?id=' in url:
                return Response("""{"bugs": [
                    {"id": "987",
                     "product": "allizom.org",
                     "summary": "Summary 1"},
                    {"id": "654",
                     "product": "mozilla.org",
                     "summary": "Summary 2"}
                ]}""")

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

    @mock.patch('requests.get')
    def test_home(self, rget):
        url = reverse('crashstats:home', args=('WaterWolf',))

        def mocked_get(url, params, **options):
            if '/products' in url and 'versions' not in params:
                return Response("""
                    {
                        "products": [
                            "WaterWolf"
                        ],
                        "hits": {
                            "WaterWolf": [{
                            "featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                            }]
                        },
                        "total": 1
                    }
                """)
            elif '/products' in url:
                return Response("""
                    {
                        "hits": [{
                            "is_featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "WaterWolf",
                            "build_type": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                        }],
                        "total": 1
                    }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # Testing with unknown product
        url = reverse('crashstats:home', args=('InternetExplorer',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        # Testing with unknown version for product
        url = reverse('crashstats:home', args=('WaterWolf', '99'))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        # Testing with valid version for product
        url = reverse('crashstats:home', args=('WaterWolf', '19.0'))
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_frontpage_json(self, rget):
        url = reverse('crashstats:frontpage_json')

        def mocked_get(url, params, **options):
            if '/crashes/daily' in url:
                return Response("""
                    {
                      "hits": {
                        "WaterWolf:19.0": {
                          "2012-10-08": {
                            "product": "WaterWolf",
                            "adu": 30000,
                            "crash_hadu": 71.099999999999994,
                            "version": "19.0",
                            "report_count": 2133,
                            "date": "2012-10-08"
                          },
                          "2012-10-02": {
                            "product": "WaterWolf",
                            "adu": 30000,
                            "crash_hadu": 77.299999999999997,
                            "version": "19.0",
                            "report_count": 2319,
                            "date": "2012-10-02"
                         }
                        }
                      }
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {'product': 'WaterWolf'})
        eq_(response.status_code, 200)

        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        ok_(struct['product_versions'])
        eq_(struct['count'], 1)

    @mock.patch('requests.get')
    def test_frontpage_json_bad_request(self, rget):
        url = reverse('crashstats:frontpage_json')

        def mocked_get(url, params, **options):
            assert '/crashes/daily' in url, url
            if 'product' in params and params['product'] == 'WaterWolf':
                return Response("""
                    {
                      "hits": {
                        "WaterWolf:19.0": {
                          "2012-10-08": {
                            "product": "WaterWolf",
                            "adu": 30000,
                            "crash_hadu": 71.099999999999994,
                            "version": "19.0",
                            "report_count": 2133,
                            "date": "2012-10-08"
                          },
                          "2012-10-02": {
                            "product": "WaterWolf",
                            "adu": 30000,
                            "crash_hadu": 77.299999999999997,
                            "version": "19.0",
                            "report_count": 2319,
                            "date": "2012-10-02"
                         }
                        }
                      }
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {'product': 'Neverheardof'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'versions': '999.1'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'versions': '99.9'  # mismatch
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'versions': '19.0'
        })
        eq_(response.status_code, 200)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'duration': 'xxx'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'duration': '-100'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'duration': '10'
        })
        eq_(response.status_code, 200)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'date_range_type': 'junk'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'date_range_type': 'build'
        })
        eq_(response.status_code, 200)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'date_range_type': 'report'
        })
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_frontpage_json_no_data_for_version(self, rget):
        url = reverse('crashstats:frontpage_json')

        def mocked_get(url, params, **options):
            assert '/crashes/daily' in url, url
            if 'product' in params and params['product'] == 'WaterWolf':
                return Response("""
                    {
                      "hits": {}
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'versions': '20.0'
        })
        eq_(response.status_code, 200)

        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)

        # Even though there was no data, the product_versions
        # property should still exist and be populated.
        eq_(struct['count'], 0)
        ok_(struct['product_versions'])

        selected_product = struct['product_versions'][0]
        eq_(selected_product['product'], 'WaterWolf')
        eq_(selected_product['version'], '20.0')

    @mock.patch('requests.get')
    def test_products_list(self, rget):
        url = reverse('crashstats:products_list')

        def mocked_get(url, params, **options):
            if '/products' in url:
                return Response("""
                {
                  "products": [
                    "WaterWolf",
                    "Fennec"
                  ],
                  "hits": [
                    {
                        "sort": "1",
                        "default_version": "15.0.1",
                        "release_name": "firefox",
                        "rapid_release_version": "5.0",
                        "product_name": "WaterWolf"
                    },
                    {
                        "sort": "3",
                        "default_version": "10.0.6esr",
                        "release_name": "mobile",
                        "rapid_release_version": "5.0",
                        "product_name": "Fennec"
                    }],
                    "total": "2"
                }
                """)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @mock.patch('requests.get')
    def test_gccrashes(self, rget):
        url = reverse('crashstats:gccrashes', args=('WaterWolf',))
        unknown_product_url = reverse('crashstats:gccrashes',
                                      args=('NotKnown',))
        invalid_version_url = reverse('crashstats:gccrashes',
                                      args=('WaterWolf', '99'))

        def mocked_get(**options):
            if '/products' in options['url']:
                return Response("""
                    {
                        "products": ["WaterWolf"],
                        "hits": [
                            {
                                "product": "WaterWolf",
                                "version": "20.0",
                                "release": "Nightly"
                            }
                        ],
                        "total": "1"
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

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

    @mock.patch('requests.get')
    def test_gccrashes_json(self, rget):
        url = reverse('crashstats:gccrashes_json')

        def mocked_get(url, params, **options):
            if '/gccrashes' in url:
                return Response("""
                    {
                      "hits": [
                          [
                              "20140203000001",
                              366
                          ]
                      ],
                      "total": 1
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': '2014-01-27',
            'end_date': '2014-02-04'
        })

        ok_(response.status_code, 200)
        ok_('application/json' in response['content-type'])

    @mock.patch('requests.get')
    def test_gccrashes_json_bad_request(self, rget):
        url = reverse('crashstats:gccrashes_json')

        def mocked_get(url, **options):
            if 'gccrashes/' in url:
                return Response("""
                    {
                      "hits": [
                          [
                              "20140203000001",
                              366
                          ]
                      ],
                      "total": 1
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': 'XXXXXX',  # not even close
            'end_date': '2014-02-04'
        })
        ok_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': '2014-02-33',  # crazy date
            'end_date': '2014-02-04'
        })
        ok_(response.status_code, 400)

        # same but on the end_date
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': '2014-02-13',
            'end_date': '2014-02-44'  # crazy date
        })
        ok_(response.status_code, 400)

        # start_date > end_date
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '20.0',
            'start_date': '2014-02-02',
            'end_date': '2014-01-01'  # crazy date
        })
        ok_(response.status_code, 400)

    @mock.patch('requests.get')
    def test_get_nightlies_for_product_json(self, rget):
        url = reverse('crashstats:get_nightlies_for_product_json')

        def mocked_get(**options):
            if '/products' in options['url']:
                return Response("""
                    {
                      "hits": [
                        {
                            "sort": "1",
                            "default_version": "5.0a1",
                            "release_name": "waterwolf",
                            "rapid_release_version": "5.0",
                            "product_name": "WaterWolf"
                        }],
                        "total": "1"
                    }
                    """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {'product': 'WaterWolf'})
        ok_('application/json' in response['content-type'])
        eq_(response.status_code, 200)
        ok_(response.content, ['20.0'])

        response = self.client.get(url, {'product': 'NightTrain'})
        eq_(response.status_code, 200)
        ok_(response.content, ['18.0', '19.0'])

        response = self.client.get(url, {'product': 'Unknown'})
        ok_(response.content, [])

    @mock.patch('crashstats.crashstats.models.SignaturesByBugs.get')
    @mock.patch('requests.get')
    def test_topcrasher_ranks_bybug(self, rget, rpost):
        url = reverse('crashstats:topcrasher_ranks_bybug')

        rpost.side_effect = mocked_post_threesigs

        def mocked_get(url, params, **options):
            signature_summary_data = copy.deepcopy(SAMPLE_SIGNATURE_SUMMARY)
            if '/signaturesummary' in url:
                signature_summary_data['reports']['products'] = [
                    {
                        "version_string": "18.0",
                        "percentage": "48.440",
                        "report_count": 52311,
                        "product_name": "WaterWolf",
                    },
                    {
                        "version_string": "18.0",
                        "percentage": "48.440",
                        "report_count": 52311,
                        "product_name": "NightTrain",
                    },
                    {
                        "version_string": "13.0b4",
                        "percentage": "9.244",
                        "report_count": 9983,
                        "product_name": "WaterWolf",
                    }

                ]
                return Response(signature_summary_data)

            if '/crashes/signatures' in url:
                return Response(u"""
                   {"crashes": [
                     {
                      "count": 188,
                      "mac_count": 66,
                      "content_count": 0,
                      "first_report": "2012-06-21",
                      "startup_percent": 0.0,
                      "currentRank": 0,
                      "previousRank": 1,
                      "first_report_exact": "2012-06-21T21:28:08",
                      "versions":
                          "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature 1",
                      "versions_count": 8,
                      "changeInRank": 1,
                      "plugin_count": 0,
                      "previousPercentOfTotal": 0.23144104803493501,
                      "is_gc_count": 10
                     },
                     {
                      "count": 188,
                      "mac_count": 66,
                      "content_count": 0,
                      "first_report": "2012-06-21",
                      "startup_percent": 0.0,
                      "currentRank": 0,
                      "previousRank": 1,
                      "first_report_exact": "2012-06-21T21:28:08",
                      "versions":
                          "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature 2",
                      "versions_count": 8,
                      "changeInRank": 1,
                      "plugin_count": 0,
                      "previousPercentOfTotal": 0.23144104803493501,
                      "is_gc_count": 10
                    }
                   ],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 2}
                """)
        rget.side_effect = mocked_get

        response = self.client.get(url, {'bug_number': '123456789'})
        ok_('FakeSignature 1' in response.content)
        ok_('FakeSignature 2' not in response.content)
        ok_('FakeSignature 3' in response.content)

        report_list_url = reverse('crashstats:report_list')
        report_list_url1 = (
            '%s?signature=%s' % (
                report_list_url,
                urllib.quote_plus('FakeSignature 1')
            )
        )
        ok_(report_list_url1 in response.content)
        report_list_url3 = (
            '%s?signature=%s' % (
                report_list_url,
                urllib.quote_plus('FakeSignature 3')
            )
        )
        ok_(report_list_url3 in response.content)

        # ensure that multiple products appear
        doc = pyquery.PyQuery(response.content)
        eq_(doc('td[class=product]')[0].text, 'WaterWolf')
        eq_(doc('td[class=product]')[1].text, 'NightTrain')
        eq_(response.status_code, 200)

        # we also have a signature with no active product+version
        ok_('Not found in active topcrash lists' in response.content)

        response = self.client.get(url, {'bug_number': '123bad'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_number': '1234564654564646'})
        eq_(response.status_code, 400)

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
                "hits": [
                   {"id": 123456789,
                    "signature": "Something"},
                    {"id": 22222,
                     "signature": u"FakeSignature1 \u7684 Japanese"},
                    {"id": 33333,
                     "signature": u"FakeSignature1 \u7684 Japanese"}
                ]
            }
        rpost.side_effect = mocked_post

        def mocked_get(url, params, **options):
            if '/crashes/signatures' in url:
                return Response(u"""
                   {"crashes": [
                     {
                      "count": 188,
                      "mac_count": 66,
                      "content_count": 0,
                      "first_report": "2012-06-21",
                      "startup_percent": 0.0,
                      "currentRank": 0,
                      "previousRank": 1,
                      "first_report_exact": "2012-06-21T21:28:08",
                      "versions":
                          "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature1 \u7684 Japanese",
                      "versions_count": 8,
                      "changeInRank": 1,
                      "plugin_count": 0,
                      "previousPercentOfTotal": 0.23144104803493501,
                      "is_gc_count": 10
                    }
                   ],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 0}
                """)

            if '/products' in url:
                return Response("""
                {
                  "hits": [
                    {
                        "is_featured": true,
                        "throttle": 1.0,
                        "end_date": "string",
                        "start_date": "integer",
                        "build_type": "string",
                        "product": "WaterWolf",
                        "version": "19.0",
                        "has_builds": true
                    }],
                    "total": "1"
                }
                """)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

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
        eq_(response.status_code, 404)

    def test_topcrasher_with_product_sans_release(self):
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
                return Response(u"""
                   {"crashes": [],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 0}
                """)

            if '/products' in url:
                return Response("""
                {
                  "hits": [
                    {
                        "is_featured": true,
                        "throttle": 1.0,
                        "end_date": "string",
                        "start_date": "integer",
                        "build_type": "string",
                        "product": "WaterWolf",
                        "version": "19.0",
                        "has_builds": true
                    }],
                    "total": "1"
                }
                """)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

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

            return Response("""
                  {
                    "hits": [
                      {
                        "signature": "FakeSignature",
                        "report_date": "2013-06-06",
                        "high_count": 4,
                        "medium_count": 3,
                        "low_count": 2,
                        "none_count": 1,
                        "product_name": "%s",
                        "version_string": "2.0"
                      }
                    ],
                    "total": 1
                  }
            """ % (settings.DEFAULT_PRODUCT,))
        rget.side_effect = mocked_get

        response = self.client.get(url)
        ok_(settings.LOGIN_URL in response['Location'] + '?next=%s' % url)
        ok_(response.status_code, 302)

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
        ok_(response.status_code, 200)

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

            return Response("""
                  {
                    "hits": [
                      {
                        "signature": "FakeSignature",
                        "report_date": "2013-06-06",
                        "high_count": 4,
                        "medium_count": 3,
                        "low_count": 2,
                        "none_count": 1,
                        "product_name": "%s",
                        "version_string": "123.0"
                      }
                    ],
                    "total": 1
                  }
            """ % (settings.DEFAULT_PRODUCT,))

        rget.side_effect = mocked_get

        user = self._login()
        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_exploitability')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('FakeSignature' in response.content)

    @mock.patch('requests.get')
    def test_exploitable_crashes_by_unknown_version(self, rget):
        url = reverse(
            'crashstats:exploitable_crashes',
            args=(settings.DEFAULT_PRODUCT, '999.0')
        )
        user = self._login()
        group = self._create_group_with_permission('view_exploitability')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_exploitability')

        response = self.client.get(url)
        eq_(response.status_code, 404)

    @mock.patch('requests.get')
    def test_daily(self, rget):
        url = reverse('crashstats:daily')

        def mocked_get(url, params, **options):
            eq_(params['versions'], ['20.0', '19.0'])
            if '/products' in url:
                return Response("""
                    {
                        "products": [
                            "WaterWolf",
                            "NightTrain"
                        ],
                        "hits": {
                            "WaterWolf": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "WaterWolf",
                                "release": "Nightly",
                                "version": "19.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }],
                            "NightTrain": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "NightTrain",
                                "release": "Nightly",
                                "version": "18.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }]
                        },
                        "total": 2
                    }
                """)
            if '/crashes' in url:
                # This list needs to match the versions as done in the common
                # fixtures set up in setUp() above.
                return Response("""
                       {
                         "hits": {
                           "WaterWolf:20.0": {
                             "2012-09-23": {
                               "adu": 80388,
                               "crash_hadu": 12.279,
                               "date": "2012-08-23",
                               "product": "WaterWolf",
                               "report_count": 9871,
                               "throttle": 0.1,
                               "version": "20.0"
                             }
                           },
                           "WaterWolf:19.0": {
                             "2012-08-23": {
                               "adu": 80388,
                               "crash_hadu": 12.279,
                               "date": "2012-08-23",
                               "product": "WaterWolf",
                               "report_count": 9871,
                               "throttle": 0.1,
                               "version": "19.0"
                             }
                           },
                           "WaterWolf:18.0": {
                             "2012-08-13": {
                               "adu": 80388,
                               "crash_hadu": 12.279,
                               "date": "2012-08-23",
                               "product": "WaterWolf",
                               "report_count": 9871,
                               "throttle": 0.1,
                               "version": "18.0"
                             }
                           }
                         }
                       }

                """)

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
                return Response("""
                    {
                        "products": [
                            "WaterWolf",
                            "NightTrain"
                        ],
                        "hits": {
                            "WaterWolf": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "WaterWolf",
                                "release": "Nightly",
                                "version": "19.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }],
                            "NightTrain": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "NightTrain",
                                "release": "Nightly",
                                "version": "18.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }]
                        },
                        "total": 2
                    }
                """)
            if '/crashes' in url:
                # This list needs to match the versions as done in the common
                # fixtures set up in setUp() above.
                return Response("""
                       {
                         "hits": {}
                       }

                """)

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

                return Response("""
                {
                    "hits": [],
                    "total": 0
                }
                """)

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
    def test_explosive_view_without_explosives(self, rget):
        url = reverse('crashstats:explosive')

        def mocked_get(url, params, **options):
            if '/suspicious' in url:
                return Response("""
                    {"hits": [], "total": 0}
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        resp = self.client.get(url)
        eq_(resp.status_code, 200)
        assert 'No explosive crashes found' in resp.content

    @mock.patch('requests.get')
    def test_explosive_view_with_explosives(self, rget):
        url = reverse('crashstats:explosive')

        def mocked_get(url, params, **options):
            if '/suspicious' in url:
                return Response("""
                    {"hits": [
                        {"date": "2013-09-01",
                         "signatures": ["signature1", "signature2"]
                        }
                    ], "total": 1}
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        resp = self.client.get(url)
        eq_(resp.status_code, 200)
        assert 'is explosive' in resp.content

    @mock.patch('requests.get')
    def test_explosive_data(self, rget):
        url = reverse('crashstats:explosive_data',
                      args=('signature', '2013-03-05'))

        def mocked_get(url, params, **options):
            if '/crashes/count_by_day' in url:
                return Response("""{
                    "hits": {
                        "2013-02-26": 100,
                        "2013-02-27": 100,
                        "2013-02-28": 100,
                        "2013-03-01": 100,
                        "2013-03-02": 100,
                        "2013-03-03": 100,
                        "2013-03-04": 100,
                        "2013-03-05": 100,
                        "2013-03-06": 100,
                        "2013-03-07": 100,
                        "2013-03-08": 100
                    }
                }""")

            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        response = self.client.get(url)

        eq_(response.status_code, 200)
        resp = json.loads(response.content)
        ok_('counts' in resp)

        # returns 11 days of data since we are after it.
        # the first day is 7 days prior, the last is 3 days after.
        eq_(len(resp['counts']), 11)
        eq_(resp['counts'][0][0], '2013-02-26')
        eq_(resp['counts'][0][1], 100)
        eq_(resp['counts'][-1][0], '2013-03-08')
        eq_(resp['counts'][-1][1], 100)

    @mock.patch('requests.get')
    def test_explosive_data_today(self, rget):
        now = datetime.datetime.utcnow()
        start = now - datetime.timedelta(10)

        now = now.strftime('%Y-%m-%d')
        start = start.strftime('%Y-%m-%d')

        url = reverse('crashstats:explosive_data', args=('signature', now))

        def mocked_get(url, params, **options):
            if '/crashes/count_by_day' in url:
                dates = []

                current = datetime.datetime.strptime(start, "%Y-%m-%d")
                end = datetime.datetime.strptime(now, "%Y-%m-%d")

                while current <= end:
                    dates.append(current.strftime("%Y-%m-%d"))
                    current += datetime.timedelta(1)

                return Response("""{
                    "hits": {
                        "%s": 100,
                        "%s": 100,
                        "%s": 100,
                        "%s": 100,
                        "%s": 100,
                        "%s": 100,
                        "%s": 100,
                        "%s": 100,
                        "%s": 100,
                        "%s": 100,
                        "%s": 100
                    }
                }""" % tuple(dates))

        rget.side_effect = mocked_get
        response = self.client.get(url)

        eq_(response.status_code, 200)
        resp = json.loads(response.content)
        eq_(resp['counts'][0][0], start)
        eq_(resp['counts'][0][1], 100)
        eq_(resp['counts'][-1][0], now)
        eq_(resp['counts'][-1][1], 100)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_topchangers(self, rget, rpost):
        url = reverse('crashstats:topchangers',
                      args=('WaterWolf', '19.0'))

        bad_url = reverse('crashstats:topchangers',
                          args=('SeaMonkey', '19.0'))

        bad_url2 = reverse('crashstats:topchangers',
                           args=('WaterWolf', '19.999'))

        url_wo_version = reverse('crashstats:topchangers',
                                 args=('WaterWolf',))

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if '/crashes/signatures' in url:
                return Response("""
                   {"crashes": [
                     {
                      "count": 188,
                      "mac_count": 66,
                      "content_count": 0,
                      "first_report": "2012-06-21",
                      "startup_percent": 0.0,
                      "currentRank": 0,
                      "previousRank": 1,
                      "first_report_exact": "2012-06-21T21:28:08",
                      "versions":
                          "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature1",
                      "versions_count": 8,
                      "changeInRank": 0,
                      "plugin_count": 0,
                      "previousPercentOfTotal": 0.23144104803493501,
                      "is_gc_count": 10
                    }
                   ],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 0}
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url_wo_version)
        eq_(response.status_code, 200)

        # invalid version for the product name
        response = self.client.get(bad_url)
        eq_(response.status_code, 404)

        # invalid version for the product name
        response = self.client.get(bad_url2)
        eq_(response.status_code, 404)

        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_topchangers_without_versions_redirect(self):
        response = self.client.get('/topchangers/products/WaterWolf/versions/')
        redirect_code = settings.PERMANENT_LEGACY_REDIRECTS and 301 or 302
        eq_(response.status_code, redirect_code)
        actual_url = reverse('crashstats:topchangers',
                             kwargs={'product': 'WaterWolf'})
        ok_(response['location'].endswith(actual_url))

    @mock.patch('requests.get')
    def test_signature_summary(self, rget):
        def mocked_get(url, params, **options):
            if '/signaturesummary' in url:
                assert params['report_types']
                return Response({
                    "reports": {
                        "products": [
                            {
                                "version_string": "33.0a2",
                                "percentage": "57.542",
                                "report_count": 103,
                                "product_name": "Firefox"
                            },
                        ],
                        "uptime": [
                            {
                                "category": "< 1 min",
                                "percentage": "29.126",
                                "report_count": 30
                            }
                        ],
                        "architecture": [
                            {
                                "category": "x86",
                                "percentage": "100.000",
                                "report_count": 103
                            }
                        ],
                        "flash_version": [
                            {
                                "category": "[blank]",
                                "percentage": "100.000",
                                "report_count": 103

                            }
                        ],
                        "graphics": [
                            {
                                "report_count": 24,
                                "adapter_name": None,
                                "vendor_hex": "0x8086",
                                "percentage": "23.301",
                                "vendor_name": None,
                                "adapter_hex": "0x0166"
                            }
                        ],
                        "distinct_install": [
                            {
                                "crashes": 103,
                                "version_string": "33.0a2",
                                "product_name": "Firefox",
                                "installations": 59
                            }
                        ],
                        "devices": [
                            {
                                "cpu_abi": "XXX",
                                "manufacturer": "YYY",
                                "model": "ZZZ",
                                "version": "1.2.3",
                                "report_count": 52311,
                                "percentage": "48.440",
                            }
                        ],
                        "os": [
                            {
                                "category": "Windows 8.1",
                                "percentage": "55.340",
                                "report_count": 57
                            }
                        ],
                        "process_type": [
                            {
                                "category": "Browser",
                                "percentage": "100.000",
                                "report_count": 103
                            }
                        ],
                        "exploitability": [
                            {
                                "low_count": 0,
                                "high_count": 0,
                                "null_count": 0,
                                "none_count": 4,
                                "report_date": "2014-08-12",
                                "medium_count": 0
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
                            "category": "11.9.900.117",
                            "percentage": "50.794",
                            "report_count": 320
                        },
                        {
                            "category": "11.9.900.152",
                            "percentage": "45.397",
                            "report_count": 286
                        },
                        {
                            "category": "11.7.700.224",
                            "percentage": "1.429",
                            "report_count": 9
                        }
                    ]
                elif 'sig2' in params['signature']:
                    signature_summary_data['reports']['flash_version'] = [
                        {
                            "category": "11.9.900.117",
                            "percentage": "50.794",
                            "report_count": 320
                        },
                        {
                            "category": "[blank]",
                            "percentage": "45.397",
                            "report_count": 286
                        },
                        {
                            "category": "11.7.700.224",
                            "percentage": "1.429",
                            "report_count": 9
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

    @mock.patch('requests.get')
    def test_status(self, rget):
        def mocked_get(url, **options):
            assert '/server_status' in url, url
            return Response(SAMPLE_STATUS)

        rget.side_effect = mocked_get

        url = reverse('crashstats:status')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('schema_12345' in response.content)
        ok_('017d7b3f7042ce76bc80949ae55b41d1e915ab62' in response.content)
        ok_('1035' in response.content)
        ok_('Sep 28 2012 20:30:01' in response.content)

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

    def test_your_crashes(self):
        url = reverse('crashstats:your_crashes')

        def mocked_supersearchfields(**params):
            return {
                'email': {
                    'name': 'email',
                    'query_type': 'string',
                    'namespace': 'processed_crash',
                    'form_field_choices': None,
                    'permissions_needed': ['crashstats.view_pii'],
                    'default_value': None,
                    'is_exposed': True,
                    'is_returned': True,
                    'is_mandatory': False,
                }
            }

        SuperSearchFields.implementation().get.side_effect = (
            mocked_supersearchfields
        )

        def mocked_supersearch_get(**params):
            assert '_columns' in params
            assert '_sort' in params
            assert 'email' in params
            assert params['email'] == ['test@mozilla.com']

            results = {
                'hits': [
                    {
                        'uuid': '1234abcd-ef56-7890-ab12-abcdef130802',
                        'date': '2000-01-02T00:00:00'
                    },
                    {
                        'uuid': '1234abcd-ef56-7890-ab12-abcdef130801',
                        'date': '2000-01-01T00:00:00'
                    }
                ],
                'total': 2
            }
            return results

        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        # A user needs to be signed in to see this page.
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )

        self._login()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('1234abcd-ef56-7890-ab12-abcdef130801' in response.content)
        ok_('1234abcd-ef56-7890-ab12-abcdef130802' in response.content)
        ok_('test@mozilla.com' in response.content)

    def test_your_crashes_no_data(self):
        url = reverse('crashstats:your_crashes')

        def mocked_supersearch_get(**params):
            assert 'email' in params
            assert params['email'] == ['test@mozilla.com']

            return {
                'hits': [],
                'total': 0
            }

        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        self._login()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('test@mozilla.com' in response.content)
        ok_('no crash report' in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index(self, rget, rpost):
        # using \\n because it goes into the JSON string
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1"
        comment0 = "This is a comment\\nOn multiple lines"
        comment0 += "\\npeterbe@mozilla.com"
        comment0 += "\\nwww.p0rn.com"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(SAMPLE_META % (email0, url0))
                if params['datatype'] == 'unredacted':
                    return Response(SAMPLE_UNREDACTED % (
                        dump,
                        comment0
                    ))

            if 'correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

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
        comment_transformed = (
            comment0
            .replace('\\n', '<br>')
            .replace('peterbe@mozilla.com', '(email removed)')
            .replace('www.p0rn.com', '(URL removed)')
        )
        ok_(comment_transformed in response.content)
        # but the email should have been scrubbed
        ok_('peterbe@mozilla.com' not in response.content)
        ok_(email0 not in response.content)
        ok_(url0 not in response.content)
        ok_(
            'You need to be signed in to be able to download raw dumps.'
            in response.content
        )
        # Should not be able to see sensitive key from stackwalker JSON
        ok_('&#34;sensitive&#34;' not in response.content)
        ok_('&#34;exploitability&#34;' not in response.content)

        # should be a link there to crash analysis
        ok_(settings.CRASH_ANALYSIS_URL in response.content)

        # the email address will appear if we log in
        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)
        assert user.has_perm('crashstats.view_pii')

        response = self.client.get(url)
        ok_('peterbe@mozilla.com' in response.content)
        ok_(email0 in response.content)
        ok_(url0 in response.content)
        ok_('&#34;sensitive&#34;' in response.content)
        ok_('&#34;exploitability&#34;' in response.content)
        eq_(response.status_code, 200)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_additional_raw_dump_links(self, rget, rpost):
        # using \\n because it goes into the JSON string
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1"

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response({
                        "InstallTime": "1339289895",
                        "FramePoisonSize": "4096",
                        "Theme": "classic/1.0",
                        "Version": "5.0a1",
                        "Email": "secret@email.com",
                        "Vendor": "Mozilla",
                        "URL": "farmville.com",
                        "additional_minidumps": "foo, bar,",
                    })
                if params['datatype'] == 'unredacted':
                    return Response({
                        "client_crash_date": "2012-06-11T06:08:45",
                        "dump": dump,
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

            if 'correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

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
    def test_report_index_fennecandroid_report(self, rget, rpost):
        # using \\n because it goes into the JSON string
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1"
        comment0 = "This is a comment\\nOn multiple lines"
        comment0 += "\\npeterbe@mozilla.com"
        comment0 += "\\nwww.p0rn.com"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(SAMPLE_META % (email0, url0))
                if params['datatype'] == 'unredacted':
                    raw_crash_json = SAMPLE_UNREDACTED % (
                        dump,
                        comment0
                    )
                    raw_crash_json = json.loads(raw_crash_json)
                    raw_crash_json['product'] = 'WinterSun'

                    return Response(raw_crash_json)

            if 'correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

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
        # using \\n because it goes into the JSON string
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1"
        comment0 = "This is a comment\\nOn multiple lines"
        comment0 += "\\npeterbe@mozilla.com"
        comment0 += "\\nwww.p0rn.com"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(SAMPLE_META % (email0, url0))
                if params['datatype'] == 'unredacted':
                    processed_json = SAMPLE_UNREDACTED % (dump, comment0)
                    assert '"WaterWolf"' in processed_json
                    assert '"5.0a1"' in processed_json
                    processed_json = processed_json.replace(
                        '"WaterWolf"', '"SummerWolf"'
                    )
                    processed_json = processed_json.replace(
                        '"5.0a1"', '"99.9"'
                    )
                    return Response(processed_json)

            if 'correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

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
        bad_url = reverse('crashstats:home', args=('SummerWolf',))
        ok_(bad_url not in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_correlations_failed(self, rget, rpost):
        # using \\n because it goes into the JSON string
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1"
        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"

        rpost.side_effect = mocked_post_threeothersigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(SAMPLE_META % (email0, url0))
                if params['datatype'] == 'unredacted':
                    return Response(SAMPLE_UNREDACTED % (
                        dump,
                        comment0
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
        dump = ""
        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"

        rpost.side_effect = mocked_post_threesigs

        def mocked_get(url, params, **options):
            if '/crash_data' in url:
                assert 'datatype' in params

                if params['datatype'] == 'meta':
                    return Response(SAMPLE_META % (email0, url0))
                if params['datatype'] == 'unredacted':
                    data = json.loads(
                        SAMPLE_UNREDACTED % (dump, comment0)
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
    def test_report_index_with_invalid_InstallTime(self, rget, rpost):
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
                return Response("""
                {
                  "InstallTime": "Not a number",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "%s",
                  "Vendor": "Mozilla",
                  "URL": "%s",
                  "HangID": "123456789"
                }
                """ % (email0, url0))
            if 'crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "%s",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "%s",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % (comment0, email1))
            if 'correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "dump": "%s",
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true,
                  "exploitability": "Unknown Exploitability"
                }
                """ % dump)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        ok_('<th>Install Time</th>' not in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_invalid_parsed_dump(self, rget, rpost):
        json_dump = {
            u'crash_info': {
                u'address': u'0x88',
                u'type': u'EXCEPTION_ACCESS_VIOLATION_READ'
            },
            u'main_module': 0,
            u'modules': [
                {
                    u'base_addr': u'0x980000',
                    u'debug_file': u'FlashPlayerPlugin.pdb',
                    u'debug_id': u'5F3C0D3034CA49FE9B94FC97EBF590A81',
                    u'end_addr': u'0xb4d000',
                    u'filename': u'FlashPlayerPlugin_13_0_0_214.exe',
                    u'version': u'13.0.0.214'},
            ],
            u'sensitive': {u'exploitability': u'none'},
            u'status': u'OK',
            u'system_info': {
                u'cpu_arch': u'x86',
                u'cpu_count': 8,
                u'cpu_info': u'GenuineIntel family 6 model 26 stepping 4',
                u'os': u'Windows NT',
                u'os_ver': u'6.0.6002 Service Pack 2'
            },
            u'thread_count': 1,
            u'threads': [{u'frame_count': 0, u'frames': []}]
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
                return Response("""
                {
                  "InstallTime": "Not a number",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "%s",
                  "Vendor": "Mozilla",
                  "URL": "%s",
                  "HangID": "123456789"
                }
                """ % (email0, url0))
            if 'crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "%s",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "%s",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % (comment0, email1))
            if 'correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "json_dump": %s,
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true,
                  "exploitability": "Unknown Exploitability"
                }
                """ % json.dumps(json_dump))

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        ok_('<th>Install Time</th>' not in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_sparse_json_dump(self, rget, rpost):
        json_dump = {u'status': u'ERROR_NO_MINIDUMP_HEADER', u'sensitive': {}}

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
                return Response("""
                {
                  "InstallTime": "Not a number",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "%s",
                  "Vendor": "Mozilla",
                  "URL": "%s",
                  "HangID": "123456789"
                }
                """ % (email0, url0))
            if 'crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "%s",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "%s",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % (comment0, email1))
            if 'correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "json_dump": %s,
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true,
                  "exploitability": "Unknown Exploitability"
                }
                """ % json.dumps(json_dump))

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_with_crash_exploitability(self, rget, rpost):
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1"
        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"
        email1 = "some@otheremailaddress.com"

        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'meta'
            ):
                return Response("""
                {
                  "InstallTime": "Not a number",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "%s",
                  "Vendor": "Mozilla",
                  "URL": "%s",
                  "HangID": "123456789"
                }
                """ % (email0, url0))
            if '/crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "%s",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "%s",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % (comment0, email1))
            if '/correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "dump": "%s",
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true,
                  "exploitability": "Unknown Exploitability"
                }
                """ % dump)

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
        ok_("Crash Not Found" in response.content)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_report_index_raw_crash_not_found(self, rget, rpost):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod|1"

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            assert '/crash_data/' in url
            assert 'datatype' in params
            if params['datatype'] == 'unredacted':
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "dump": "%s",
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true,
                  "exploitability": "Unknown Exploitability"
                }
                """ % dump)
            elif params['datatype'] == 'meta':  # raw crash json!
                raise models.BadStatusCodeError(404)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_("Crash Not Found" in response.content)

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
                ok_(urllib.quote_plus(sig) in link.attrib['href'])

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
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "release_channel": "Release",
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:0",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "release_channel": "Release",
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    }
                    ],
                    "total": 2
                    }
                """)
            if 'correlations/signatures' in url:
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "release_channel": "Release",
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "release_channel": "Release",
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:0",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    }
                    ],
                    "total": 2
                    }
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('correlations',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        # relevant data is put into 'data' attributes
        ok_('data-correlation_version="5.0a1"' in response.content)
        ok_('data-correlation_os="Mac OS X"' in response.content)

    @mock.patch('requests.get')
    def test_report_list_partial_correlations_no_data(self, rget):

        def mocked_get(url, params, **options):
            if 'report/list' in url:
                return Response("""
                {
                  "hits": [],
                  "total": 2
                }
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats:report_list_partial', args=('correlations',))
        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)
        # relevant data is put into 'data' attributes
        ok_('data-correlation_version=""' in response.content)
        ok_('data-correlation_os=""' in response.content)

    @mock.patch('requests.get')
    def test_report_list_partial_sigurls(self, rget):

        def mocked_get(url, params, **options):
            # no specific product was specified, then it should be all products
            ok_('products' in params)
            ok_(settings.DEFAULT_PRODUCT not in params['products'])
            ok_('ALL' in params['products'])

            if '/signatureurls' in url:
                return Response({
                    "hits": [
                        {"url": "http://farm.ville", "crash_count": 123}
                    ],
                    "total": 2
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
                return Response("""{
                    "hits": [
                        {"url": "http://farm.ville", "crash_count":123},
                        {"url": "%s", "crash_count": 1}
                    ],
                    "total": 2
                }
                """ % (really_long_url))

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
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "I LOVE CHEESE cheese@email.com",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "bob@uncle.com",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
                """)

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
                        "hits": [{
                            "user_comments": "I LOVE HAM",
                            "date_processed": "2012-08-21T11:17:28-07:00",
                            "email": "bob@uncle.com",
                            "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                        }],
                        "total": 2
                    })
                else:
                    return Response({
                        "hits": [{
                            "user_comments": "I LOVE CHEESE",
                            "date_processed": "2011-08-21T11:17:28-07:00",
                            "email": "bob@uncle.com",
                            "uuid": "469bde48-0e8f-3586-d486-b98810120829"
                        }],
                        "total": 2
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
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    }
                    ],
                    "total": 2
                    }
                """)
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
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T22:19:59+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    }
                    ],
                    "total": 2
                    }
                """)
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
        ok_('reverse' not in mock_calls[-1])

    @mock.patch('requests.get')
    def test_report_list_partial_reports_columns_override(self, rget):

        def mocked_get(url, params, **options):
            if 'report/list' in url:
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    }
                    ],
                    "total": 2
                    }
                """)
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
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null,
                      "raw_crash": {
                          "Winsock_LSP": "Peter",
                          "SecondsSinceLastCrash": "Bengtsson"
                      }
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null,
                      "raw_crash": null
                    }
                    ],
                    "total": 2
                    }
                """)
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
                    "user_comments": None,
                    "product": "WaterWolf",
                    "os_name": "Linux",
                    "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                    "cpu_info": "...",
                    "url": "http://example.com/116",
                    "last_crash": 1234,
                    "date_processed": "2012-09-05T21:18:58+00:00",
                    "cpu_name": "x86",
                    "uptime": 1234,
                    "process_type": "browser",
                    "hangid": None,
                    "reason": "reason7",
                    "version": "5.0a1",
                    "os_version": "1.2.3.4",
                    "build": "20120901000007",
                    "install_age": 1234,
                    "signature": "FakeSignature",
                    "install_time": "2012-09-05T20:58:24+00:00",
                    "address": "0xdeadbeef",
                    "duplicate_of": None
                }
                hits = []

                for i in range(result_offset, result_offset + result_number):
                    try:
                        item = dict(first, uuid=uuids[i])
                        hits.append(item)
                    except IndexError:
                        break

                return Response(json.dumps({
                    "hits": hits,
                    "total": len(uuids)
                }))
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
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    }
                    ],
                    "total": 2
                    }
                """)

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
                "hits": [
                    {"id": 111111,
                     "signature": "Something"},
                    {"id": 123456789,
                     "signature": "Something"}
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
                return Response("""
                {
                  "hits": [
                    {
                     "count": 1050,
                     "build_date": "20130806030203",
                     "count_mac": 0,
                     "frequency_windows": 1.0,
                     "count_windows": 1050,
                     "frequency": 1.0,
                     "count_linux": 0,
                     "total": 1050,
                     "frequency_linux": 0.0,
                     "frequency_mac": 0.0
                   },
                   {
                     "count": 1150,
                     "build_date": "notadate",
                     "count_mac": 0,
                     "frequency_windows": 1.0,
                     "count_windows": 1150,
                     "frequency": 1.0,
                     "count_linux": 0,
                     "total": 1150,
                     "frequency_linux": 0.0,
                     "frequency_mac": 0.0
                   },
                   {
                     "count": 1250,
                     "build_date": null,
                     "count_mac": 0,
                     "frequency_windows": 1.0,
                     "count_windows": 1250,
                     "frequency": 1.0,
                     "count_linux": 0,
                     "total": 1250,
                     "frequency_linux": 0.0,
                     "frequency_mac": 0.0
                   }

                  ]
                }
                """)

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
                return Response("""
                {
                  "InstallTime": "1339289895",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "%s",
                  "Vendor": "Mozilla",
                  "URL": "%s"
                }
                """ % (email0, url0))
            if 'crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "%s",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "%s",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % (comment0, email1))

            if (
                '/crash_data' in url and
                'datatype' in params and
                params['datatype'] == 'unredacted'
            ):
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "dump": "%s",
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true,
                  "exploitability": "Unknown Exploitability"
                }
                """ % dump)

            if 'correlations/signatures' in url:
                return Response("""
                {
                    "hits": [
                        "FakeSignature1",
                        "FakeSignature2"
                    ],
                    "total": 2
                }
                """)

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
                return Response("""
                {
                  "hits": [],
                  "total": 0
                }
                """)
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
                return Response("""
                  {"foo": "bar",
                   "stuff": 123}
                """)

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
            {"foo": "bar", "stuff": 123})

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

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_remembered_date_range_type(self, rget, rpost):
        # if you visit the home page, the default date_range_type will be
        # 'report' but if you switch to 'build' it'll remember that

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if '/products' in url and 'versions' not in params:
                return Response("""
                    {
                        "products": [
                            "WaterWolf"
                        ],
                        "hits": {
                            "WaterWolf": [{
                            "featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                            }]
                        },
                        "total": 1
                    }
                """)
            elif '/products' in url:
                return Response("""
                    {
                        "hits": [{
                            "is_featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "WaterWolf",
                            "build_type": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                        }],
                        "total": 1
                    }
                """)

            if '/crashes/daily' in url:
                return Response("""
                    {
                      "hits": {
                        "WaterWolf:19.0": {
                          "2012-10-08": {
                            "product": "WaterWolf",
                            "adu": 30000,
                            "crash_hadu": 71.099999999999994,
                            "version": "19.0",
                            "report_count": 2133,
                            "date": "2012-10-08"
                          },
                          "2012-10-02": {
                            "product": "WaterWolf",
                            "adu": 30000,
                            "crash_hadu": 77.299999999999997,
                            "version": "19.0",
                            "report_count": 2319,
                            "date": "2012-10-02"
                         }
                        }
                      }
                    }
                    """)
            if '/crashes/signatures' in url:
                return Response("""
                   {"crashes": [
                     {
                      "count": 188,
                      "mac_count": 66,
                      "content_count": 0,
                      "first_report": "2012-06-21",
                      "startup_percent": 0.0,
                      "currentRank": 0,
                      "previousRank": 1,
                      "first_report_exact": "2012-06-21T21:28:08",
                      "versions":
                          "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature1",
                      "versions_count": 8,
                      "changeInRank": 0,
                      "plugin_count": 0,
                      "previousPercentOfTotal": 0.23144104803493501,
                      "is_gc_count": 10
                    }
                   ],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 0}
                """)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats:home', args=('WaterWolf',))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        regex = re.compile('(<a\s+href="\?date_range_type=(\w+)[^>]+)')
        for tag, value in regex.findall(response.content):
            if value == 'report':
                ok_('selected' in tag)
            else:
                ok_('selected' not in tag)

        # now, like the home page does, fire of an AJAX request to frontpage
        # for 'build' instead
        frontpage_json_url = reverse('crashstats:frontpage_json')
        frontpage_reponse = self.client.get(frontpage_json_url, {
            'product': 'WaterWolf',
            'date_range_type': 'build'
        })
        eq_(frontpage_reponse.status_code, 200)

        # load the home page again, and it should be on build date instead
        response = self.client.get(url)
        eq_(response.status_code, 200)
        for tag, value in regex.findall(response.content):
            if value == 'build':
                ok_('selected' in tag)
            else:
                ok_('selected' not in tag)

        # open topcrashers with 'report'
        topcrasher_report_url = reverse(
            'crashstats:topcrasher',
            kwargs={
                'product': 'WaterWolf',
                'versions': '19.0',
                'date_range_type': 'report'
            }
        )
        response = self.client.get(topcrasher_report_url)
        eq_(response.status_code, 200)

        # now, go back to the home page, and 'report' should be the new default
        response = self.client.get(url)
        eq_(response.status_code, 200)
        for tag, value in regex.findall(response.content):
            if value == 'report':
                ok_('selected' in tag)
            else:
                ok_('selected' not in tag)

        # open topcrashers with 'build'
        topcrasher_report_url = reverse(
            'crashstats:topcrasher',
            kwargs={
                'product': 'WaterWolf',
                'versions': '19.0',
                'date_range_type': 'build'
            }
        )
        response = self.client.get(topcrasher_report_url)
        eq_(response.status_code, 200)

        # now, go back to the home page, and 'report' should be the new default
        response = self.client.get(url)
        eq_(response.status_code, 200)
        for tag, value in regex.findall(response.content):
            if value == 'build':
                ok_('selected' in tag)
            else:
                ok_('selected' not in tag)

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
            {'correlation_report_type': 'core-counts',
             'product': 'WaterWolf',
             'version': '19.0',
             'platform': 'Windows NT',
             'signature': 'FakeSignature'}
        )

        ok_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        eq_(struct['reason'], 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS')

    @mock.patch('requests.get')
    def test_correlations_signatures_json(self, rget):
        url = reverse('crashstats:correlations_signatures_json')

        def mocked_get(url, params, **options):
            if '/correlations/' in url:
                return Response({
                    "hits": ["FakeSignature1",
                             "FakeSignature2"],
                    "total": 2
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(
            url,
            {'correlation_report_type': 'core-counts',
             'product': 'WaterWolf',
             'version': '19.0',
             'platforms': 'Windows NT,Linux'}
        )
        ok_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        eq_(struct['total'], 2)

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

    def test_your_permissions_page(self):
        url = reverse('crashstats:permissions')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(user.email in response.content)

        # make some groups and attach permissions
        self._create_group_with_permission(
            'view_pii', 'Group A'
        )
        groupB = self._create_group_with_permission(
            'view_exploitability', 'Group B'
        )
        user.groups.add(groupB)
        assert not user.has_perm('crashstats.view_pii')
        assert user.has_perm('crashstats.view_exploitability')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(PERMISSIONS['view_pii'] in response.content)
        ok_(PERMISSIONS['view_exploitability'] in response.content)
        doc = pyquery.PyQuery(response.content)
        for row in doc('table.permissions tbody tr'):
            cells = []
            for td in doc('td', row):
                cells.append(td.text.strip())
            if cells[0] == PERMISSIONS['view_pii']:
                eq_(cells[1], 'No')
            elif cells[0] == PERMISSIONS['view_exploitability']:
                eq_(cells[1], 'Yes!')
