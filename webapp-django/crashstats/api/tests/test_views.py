import contextlib
import json

from django.core.cache import cache
from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import timezone

from markus.testing import MetricsMock
import mock
from moto import mock_s3_deprecated
import pyquery

from crashstats.base.tests.testbase import TestCase
from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.supersearch.models import SuperSearch, SuperSearchUnredacted
from crashstats.crashstats.models import (
    Bugs,
    CrontabberState,
    ProcessedCrash,
    ProductVersions,
    Reprocessing,
    RawCrash,
    SignaturesByBugs,
    SocorroCommon,
    UnredactedCrash,
)
from crashstats.tokens.models import Token
from socorro.lib import BadArgumentError, MissingArgumentError
from socorro.lib.ooid import create_new_ooid
from socorro.unittest.external.boto.conftest import BotoHelper


class TestDedentLeft(TestCase):

    def test_dedent_left(self):
        from crashstats.api.views import dedent_left
        assert dedent_left('Hello', 2) == 'Hello'
        assert dedent_left('   Hello', 2) == ' Hello'
        assert dedent_left('   Hello ', 2) == ' Hello '

        text = """Line 1
        Line 2
        Line 3
        """.rstrip()
        # because this code right above is indented with 2 * 4 spaces
        assert dedent_left(text, 8) == 'Line 1\nLine 2\nLine 3'


class TestDocumentationViews(BaseTestViews):

    def test_documentation_home_page(self):

        url = reverse('api:documentation')
        response = self.client.get(url)
        assert response.status_code == 200

        doc = pyquery.PyQuery(response.content)

        from crashstats.api import views
        for elt in doc('#mainbody .panel .title h2 a'):
            assert elt.text not in views.BLACKLIST


class TestViews(BaseTestViews):

    def setUp(self):
        super(TestViews, self).setUp()
        self._middleware_classes = settings.MIDDLEWARE_CLASSES
        settings.MIDDLEWARE_CLASSES += (
            'crashstats.crashstats.middleware.SetRemoteAddrFromRealIP',
        )

    def tearDown(self):
        super(TestViews, self).tearDown()
        settings.MIDDLEWARE_CLASSES = self._middleware_classes

    def test_invalid_url(self):
        url = reverse('api:model_wrapper', args=('BlaBLabla',))
        response = self.client.get(url)
        assert response.status_code == 404

    def test_base_classes_raise_not_found(self):
        url = reverse('api:model_wrapper', args=('SocorroMiddleware',))
        response = self.client.get(url)
        assert response.status_code == 404

        url = reverse('api:model_wrapper', args=('ESSocorroMiddleware',))
        response = self.client.get(url)
        assert response.status_code == 404

    def test_CORS(self):
        """any use of model_wrapper should return a CORS header"""

        def mocked_get(**options):
            dt = timezone.now()
            return {
                "state": {
                    "automatic-emails": {
                        "next_run": dt,
                        "first_run": dt,
                        "depends_on": [],
                        "last_run": dt,
                        "last_success": dt,
                        "error_count": 0,
                        "last_error": {}
                    },
                    "ftpscraper": {
                        "next_run": dt,
                        "first_run": dt,
                        "depends_on": [],
                        "last_run": dt,
                        "last_success": dt,
                        "error_count": 0,
                        "last_error": {}
                    }
                }
            }

        CrontabberState.implementation().get.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('CrontabberState',))
        response = self.client.get(url)
        assert response.status_code == 200
        assert response['Access-Control-Allow-Origin'] == '*'

    def test_cache_control(self):
        """successful queries against models with caching should
        set a Cache-Control header."""

        def mocked_get(**options):
            assert options['product'] == [settings.DEFAULT_PRODUCT]
            return {
                "hits": [
                    {
                        "product": settings.DEFAULT_PRODUCT,
                        "throttle": 100.0,
                        "end_date": "2018-10-29",
                        "is_featured": True,
                        "build_type": "nightly",
                        "version": "63.0a1",
                        "start_date": "2018-06-25",
                        "has_builds": True,
                        "is_rapid_beta": False
                    },
                ]
            }

        ProductVersions.implementation().get.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('ProductVersions',))
        response = self.client.get(url, {'product': settings.DEFAULT_PRODUCT})
        assert response.status_code == 200
        assert response['Cache-Control']
        assert 'private' in response['Cache-Control']
        cache_seconds = ProductVersions.cache_seconds
        assert 'max-age={}'.format(cache_seconds) in response['Cache-Control']

    def test_ProductVersions(self):

        def mocked_get(*args, **k):
            return {
                'hits': [
                    {
                        'product': 'Firefox',
                        'version': '1.0',
                    }
                ],
                'total': 1
            }
            raise NotImplementedError

        ProductVersions.implementation().get.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('ProductVersions',))
        response = self.client.get(url)
        assert response.status_code == 200
        dump = json.loads(response.content)
        assert dump['total'] == 1
        expected = {
            'product': 'Firefox',
            'version': '1.0',
        }
        assert dump['hits'][0] == expected

    def test_metrics_gathering(self):
        # note: this gets mocked out in the setUp
        url = reverse('api:model_wrapper', args=('Platforms',))
        with MetricsMock() as metrics_mock:
            response = self.client.get(url)
        assert response.status_code == 200
        assert metrics_mock.has_record(
            fun_name='incr',
            stat='webapp.api.pageview',
            value=1,
            tags=['endpoint:apiPlatforms']
        )

    def test_Platforms(self):
        # note: this gets mocked out in the setUp
        url = reverse('api:model_wrapper', args=('Platforms',))
        response = self.client.get(url)
        assert response.status_code == 200
        dump = json.loads(response.content)
        # see the setUp for this fixture
        assert dump[0] == {'code': 'win', 'name': 'Windows'}

    def test_ProcessedCrash(self):
        url = reverse('api:model_wrapper', args=('ProcessedCrash',))
        response = self.client.get(url)
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json; charset=UTF-8'
        dump = json.loads(response.content)
        assert dump['errors']['crash_id']

        def mocked_get(**params):
            if 'datatype' in params and params['datatype'] == 'processed':
                return {
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
                    "upload_file_minidump_browser": "a crash",
                    "upload_file_minidump_flash1": "a crash",
                    "upload_file_minidump_flash2": "a crash",
                    "upload_file_minidump_plugin": "a crash"
                }
            raise NotImplementedError

        ProcessedCrash.implementation().get.side_effect = mocked_get

        response = self.client.get(url, {
            'crash_id': '123',
        })
        assert response.status_code == 200
        dump = json.loads(response.content)
        assert dump['uuid'] == u'11cb72f5-eb28-41e1-a8e4-849982120611'
        assert 'upload_file_minidump_flash2' in dump
        assert 'url' not in dump

    def test_UnredactedCrash(self):
        url = reverse('api:model_wrapper', args=('UnredactedCrash',))
        response = self.client.get(url)
        # because we don't have the sufficient permissions yet to use it
        assert response.status_code == 403

        user = User.objects.create(username='test')
        self._add_permission(user, 'view_pii')
        self._add_permission(user, 'view_exploitability')
        view_pii_perm = Permission.objects.get(
            codename='view_pii'
        )
        token = Token.objects.create(
            user=user,
            notes="Only PII token"
        )
        view_exploitability_perm = Permission.objects.get(
            codename='view_exploitability'
        )
        token.permissions.add(view_pii_perm)
        token.permissions.add(view_exploitability_perm)

        response = self.client.get(url, HTTP_AUTH_TOKEN=token.key)
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json; charset=UTF-8'
        dump = json.loads(response.content)
        assert dump['errors']['crash_id']

        def mocked_get(**params):
            if 'datatype' in params and params['datatype'] == 'unredacted':
                return {
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
                    "upload_file_minidump_browser": "a crash",
                    "upload_file_minidump_flash1": "a crash",
                    "upload_file_minidump_flash2": "a crash",
                    "upload_file_minidump_plugin": "a crash",
                    "exploitability": "Unknown Exploitability",
                }
            raise NotImplementedError

        UnredactedCrash.implementation().get.side_effect = mocked_get

        response = self.client.get(url, {
            'crash_id': '123',
        }, HTTP_AUTH_TOKEN=token.key)
        assert response.status_code == 200
        dump = json.loads(response.content)
        assert dump['uuid'] == u'11cb72f5-eb28-41e1-a8e4-849982120611'
        assert 'upload_file_minidump_flash2' in dump
        assert 'exploitability' in dump

    def test_RawCrash(self):

        def mocked_get(**params):
            if 'uuid' in params and params['uuid'] == 'abc123':
                return {
                    "InstallTime": "1366691881",
                    "AdapterVendorID": "0x8086",
                    "Theme": "classic/1.0",
                    "Version": "23.0a1",
                    "id": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
                    "Vendor": "Mozilla",
                    "EMCheckCompatibility": "true",
                    "Throttleable": "0",
                    "URL": "http://system.gaiamobile.org:8080/",
                    "version": "23.0a1",
                    "AdapterDeviceID": "0x  46",
                    "ReleaseChannel": "nightly",
                    "submitted_timestamp": "2013-04-29T16:42:28.961187+00:00",
                    "buildid": "20130422105838",
                    "timestamp": 1367253748.9612169,
                    "Notes": "AdapterVendorID: 0x8086, AdapterDeviceID: ...",
                    "CrashTime": "1366703112",
                    "FramePoisonBase": "7ffffffff0dea000",
                    "FramePoisonSize": "4096",
                    "StartupTime": "1366702830",
                    "Add-ons": "activities%40gaiamobile.org:0.1,%40gaiam...",
                    "BuildID": "20130422105838",
                    "SecondsSinceLastCrash": "23484",
                    "ProductName": "WaterWolf",
                    "legacy_processing": 0,
                    "ProductID": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
                    "AsyncShutdownTimeout": 12345,
                    "BIOS_Manufacturer": "abc123",
                    "Comments": "I visited http://example.com and mail@example.com",
                    "upload_file_minidump_browser": "a crash",
                    "upload_file_minidump_flash1": "a crash",
                    "upload_file_minidump_flash2": "a crash",
                    "upload_file_minidump_plugin": "a crash"
                }
            raise NotImplementedError

        RawCrash.implementation().get.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('RawCrash',))
        response = self.client.get(url)
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json; charset=UTF-8'
        dump = json.loads(response.content)
        assert dump['errors']['crash_id']

        response = self.client.get(url, {
            'crash_id': 'abc123'
        })
        assert response.status_code == 200
        dump = json.loads(response.content)
        assert 'id' in dump
        assert 'URL' not in dump
        assert 'AsyncShutdownTimeout' in dump
        assert 'BIOS_Manufacturer' in dump
        assert 'upload_file_minidump_browser' in dump
        assert 'upload_file_minidump_flash1' in dump
        assert 'upload_file_minidump_flash2' in dump
        assert 'upload_file_minidump_plugin' in dump

    def test_RawCrash_binary_blob(self):

        def mocked_get(**params):
            if 'uuid' in params and params['uuid'] == 'abc':
                return '\xe0'
            raise NotImplementedError

        RawCrash.implementation().get.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('RawCrash',))
        response = self.client.get(url, {
            'crash_id': 'abc',
            'format': 'raw'
        })
        # because we don't have permission
        assert response.status_code == 403

        response = self.client.get(url, {
            'crash_id': 'abc',
            'format': 'wrong'  # note
        })
        # invalid format
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json; charset=UTF-8'

        user = self._login()
        self._add_permission(user, 'view_pii')
        response = self.client.get(url, {
            'crash_id': 'abc',
            'format': 'raw'
        })
        # still don't have the right permission
        assert response.status_code == 403

        self._add_permission(user, 'view_rawdump')
        response = self.client.get(url, {
            'crash_id': 'abc',
            'format': 'raw'
        })
        # finally!
        assert response.status_code == 200
        assert response['Content-Disposition'] == 'attachment; filename="abc.dmp"'
        assert response['Content-Type'] == 'application/octet-stream'

    def test_RawCrash_invalid_crash_id(self):
        # NOTE(alexisdeschamps): this undoes the mocking of the implementation so we can test
        # the implementation code.
        RawCrash.implementation = self._mockeries[RawCrash]
        url = reverse('api:model_wrapper', args=('RawCrash',))
        response = self.client.get(url, {
            'crash_id': '821fcd0c-d925-4900-85b6-687250180607docker/as_me.sh'
        })
        assert response.status_code == 400

    def test_Bugs(self):
        url = reverse('api:model_wrapper', args=('Bugs',))
        response = self.client.get(url)
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json; charset=UTF-8'
        dump = json.loads(response.content)
        assert dump['errors']['signatures']

        def mocked_get_bugs(**options):
            return {
                "hits": [
                    {
                        "id": "123456789",
                        "signature": "Something"
                    }
                ]
            }
        Bugs.implementation().get.side_effect = mocked_get_bugs

        response = self.client.get(url, {
            'signatures': 'one & two',
        })
        assert response.status_code == 200
        dump = json.loads(response.content)
        assert dump['hits']

    def test_SignaturesForBugs(self):

        def mocked_get_bugs(**options):
            return {
                "hits": [
                    {"id": "123456789", "signature": "Something"}
                ]
            }
        SignaturesByBugs.implementation().get.side_effect = mocked_get_bugs

        url = reverse('api:model_wrapper', args=('SignaturesByBugs',))
        response = self.client.get(url)
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json; charset=UTF-8'
        dump = json.loads(response.content)
        assert dump['errors']['bug_ids']

        response = self.client.get(url, {
            'bug_ids': '123456789',
        })
        assert response.status_code == 200
        dump = json.loads(response.content)
        assert dump['hits']

    def test_NewSignatures(self):

        def mocked_supersearch_get(**params):
            assert params['product'] == [settings.DEFAULT_PRODUCT]

            if 'version' in params:
                assert params['version'] == ['1.0', '2.0']

            if 'signature' not in params:
                # Return a list of signatures.
                signatures = [
                    {'term': 'ba', 'count': 21},
                    {'term': 'zin', 'count': 19},
                    {'term': 'ga', 'count': 1},
                ]
            else:
                # Return only some of the above signatures. The missing ones
                # are "new" signatures.
                signatures = [
                    {'term': 'ga', 'count': 21},
                ]

            return {
                'hits': [],
                'facets': {
                    'signature': signatures
                },
                'total': 43829,
            }

        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        url = reverse('api:model_wrapper', args=('NewSignatures',))

        # Test we get expected results.
        response = self.client.get(url)
        assert response.status_code == 200

        res_expected = [
            'ba',
            'zin',
        ]
        res = json.loads(response.content)
        assert res['hits'] == res_expected

        # Test with versions.
        response = self.client.get(url, {
            'version': ['1.0', '2.0']
        })
        assert response.status_code == 200

        # Test with incorrect arguments.
        response = self.client.get(url, {
            'start_date': 'not a date',
            'end_date': 'not a date',
            'not_after': 'not a date',
        })
        assert response.status_code == 400
        assert response['Content-Type'] == 'application/json; charset=UTF-8'
        res = json.loads(response.content)
        assert 'errors' in res
        assert len(res['errors']) == 3

    def test_CrontabberState(self):
        # The actual dates dont matter, but it matters that it's a
        # datetime.datetime object.

        def mocked_get(**options):
            dt = timezone.now()
            return {
                "state": {
                    "automatic-emails": {
                        "next_run": dt,
                        "first_run": dt,
                        "depends_on": [],
                        "last_run": dt,
                        "last_success": dt,
                        "error_count": 0,
                        "last_error": {}
                    },
                    "ftpscraper": {
                        "next_run": dt,
                        "first_run": dt,
                        "depends_on": [],
                        "last_run": dt,
                        "last_success": dt,
                        "error_count": 0,
                        "last_error": {}
                    }
                }
            }

        CrontabberState.implementation().get.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('CrontabberState',))
        response = self.client.get(url)
        assert response.status_code == 200
        dump = json.loads(response.content)
        assert dump['state']

    def test_Field(self):
        url = reverse('api:model_wrapper', args=('Field',))
        response = self.client.get(url)
        assert response.status_code == 404

    def test_hit_or_not_hit_ratelimit(self):

        def mocked_get(**options):
            dt = timezone.now()
            return {
                "state": {
                    "automatic-emails": {
                        "next_run": dt,
                        "first_run": dt,
                        "depends_on": [],
                        "last_run": dt,
                        "last_success": dt,
                        "error_count": 0,
                        "last_error": {}
                    },
                    "ftpscraper": {
                        "next_run": dt,
                        "first_run": dt,
                        "depends_on": [],
                        "last_run": dt,
                        "last_success": dt,
                        "error_count": 0,
                        "last_error": {}
                    },
                }
            }

        CrontabberState.implementation().get.side_effect = mocked_get

        # doesn't matter much which model we use
        url = reverse('api:model_wrapper', args=('CrontabberState',))

        response = self.client.get(url)
        assert response.status_code == 200
        with self.settings(
            API_RATE_LIMIT='3/m',
            API_RATE_LIMIT_AUTHENTICATED='6/m'
        ):
            current_limit = 3  # see above mentioned settings override
            # Double to avoid
            # https://bugzilla.mozilla.org/show_bug.cgi?id=1148470
            for __ in range(current_limit * 2):
                response = self.client.get(url, HTTP_X_REAL_IP='12.12.12.12')
            assert response.status_code == 429

            # But it'll work if you use a different X-Real-IP
            # because the rate limit is based on your IP address
            response = self.client.get(url, HTTP_X_REAL_IP='11.11.11.11')
            assert response.status_code == 200

            user = User.objects.create(username='test')
            token = Token.objects.create(
                user=user,
                notes="Just for avoiding rate limit"
            )

            response = self.client.get(url, HTTP_AUTH_TOKEN=token.key)
            assert response.status_code == 200

            for __ in range(current_limit):
                response = self.client.get(url)
            assert response.status_code == 200

            # But even being signed in has a limit.
            authenticated_limit = 6  # see above mentioned settings override
            assert authenticated_limit > current_limit
            for __ in range(authenticated_limit * 2):
                response = self.client.get(url)
            # Even if you're authenticated - sure the limit is higher -
            # eventually you'll run into the limit there too.
            assert response.status_code == 429

    def test_SuperSearch(self):

        def mocked_supersearch_get(**params):
            assert 'exploitability' not in params

            restricted_params = (
                '_facets',
                '_aggs.signature',
                '_histogram.date',
            )
            for key in restricted_params:
                if key in params:
                    assert 'url' not in params[key]
                    assert 'email' not in params[key]
                    assert '_cardinality.email' not in params[key]

            if 'product' in params:
                assert params['product'] == ['WaterWolf', 'NightTrain']

            return {
                'hits': [
                    {
                        'signature': 'abcdef',
                        'product': 'WaterWolf',
                        'version': '1.0',
                        'email': 'thebig@lebowski.net',
                        'exploitability': 'high',
                        'url': 'http://embarassing.website.com',
                        'user_comments': 'hey I am thebig@lebowski.net',
                    }
                ],
                'facets': {
                    'signature': []
                },
                'total': 0
            }

        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        url = reverse('api:model_wrapper', args=('SuperSearch',))
        response = self.client.get(url)
        assert response.status_code == 200
        res = json.loads(response.content)

        assert res['hits']
        assert res['facets']

        # Verify forbidden fields are not exposed.
        assert 'email' not in res['hits']
        assert 'exploitability' not in res['hits']
        assert 'url' not in res['hits']

        # Verify it's not possible to use restricted parameters.
        response = self.client.get(url, {
            'exploitability': 'high',
            '_facets': ['url', 'email', 'product', '_cardinality.email'],
            '_aggs.signature': [
                'url', 'email', 'product', '_cardinality.email'
            ],
            '_histogram.date': [
                'url', 'email', 'product', '_cardinality.email'
            ],
        })
        assert response.status_code == 200

        # Verify values can be lists.
        response = self.client.get(url, {
            'product': ['WaterWolf', 'NightTrain']
        })
        assert response.status_code == 200

    def test_SuperSearchUnredacted(self):

        def mocked_supersearch_get(**params):
            assert 'exploitability' in params
            if 'product' in params:
                assert params['product'] == ['WaterWolf', 'NightTrain']
            return {
                'hits': [
                    {
                        'signature': 'abcdef',
                        'product': 'WaterWolf',
                        'version': '1.0',
                        'email': 'thebig@lebowski.net',
                        'exploitability': 'high',
                        'url': 'http://embarassing.website.com',
                        'user_comments': 'hey I am thebig@lebowski.net',
                    }
                ],
                'facets': {
                    'signature': []
                },
                'total': 0
            }

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        url = reverse('api:model_wrapper', args=('SuperSearchUnredacted',))
        response = self.client.get(url, {'exploitability': 'high'})
        assert response.status_code == 403
        assert response['Content-Type'] == 'application/json'
        error = json.loads(response.content)['error']
        permission = Permission.objects.get(
            codename='view_exploitability'
        )
        assert permission.name in error

        # Log in to get permissions.
        user = self._login()
        self._add_permission(user, 'view_pii')
        self._add_permission(user, 'view_exploitability')

        response = self.client.get(url, {'exploitability': 'high'})
        assert response.status_code == 200
        res = json.loads(response.content)

        assert res['hits']
        assert res['facets']

        # Verify forbidden fields are exposed.
        assert 'email' in res['hits'][0]
        assert 'exploitability' in res['hits'][0]
        assert 'url' in res['hits'][0]
        assert 'thebig@lebowski.net' in res['hits'][0]['user_comments']

        # Verify values can be lists.
        response = self.client.get(url, {
            'exploitability': 'high',
            'product': ['WaterWolf', 'NightTrain']
        })
        assert response.status_code == 200

    def test_change_certain_exceptions_to_bad_request(self):

        # It actually doesn't matter so much which service we use
        # because we're heavily mocking it.
        # Here we use the SuperSearch model.

        def mocked_supersearch_get(**params):
            if params.get('product'):
                raise MissingArgumentError(params['product'])
            else:
                raise BadArgumentError('That was a bad thing to do')

        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        url = reverse('api:model_wrapper', args=('SuperSearch',))
        response = self.client.get(url)
        assert response.status_code == 400
        assert 'That was a bad thing to do' in response.content
        response = self.client.get(url, {'product': 'foobaz'})
        assert response.status_code == 400
        assert 'foobaz' in response.content

    def test_Reprocessing(self):

        def mocked_reprocess(crash_ids):
            assert crash_ids == ['xxxx']
            return True

        Reprocessing.implementation().reprocess = mocked_reprocess

        url = reverse('api:model_wrapper', args=('Reprocessing',))
        response = self.client.get(url)
        assert response.status_code == 403

        params = {
            'crash_ids': 'xxxx',
        }
        response = self.client.get(url, params, HTTP_AUTH_TOKEN='somecrap')
        assert response.status_code == 403

        user = User.objects.create(username='test')
        self._add_permission(user, 'reprocess_crashes')

        perm = Permission.objects.get(
            codename='reprocess_crashes'
        )
        # but make a token that only has the 'reprocess_crashes'
        # permission associated with it
        token = Token.objects.create(
            user=user,
            notes="Only reprocessing"
        )
        token.permissions.add(perm)

        response = self.client.get(url, params, HTTP_AUTH_TOKEN=token.key)
        assert response.status_code == 405

        response = self.client.post(url, params, HTTP_AUTH_TOKEN=token.key)
        assert response.status_code == 200
        assert json.loads(response.content) is True


class TestCrashVerify(object):
    @contextlib.contextmanager
    def supersearch_returns_crashes(self, uuids):
        """Mock supersearch implementation to return result with specified crashes"""
        def mocked_supersearch_get(**params):
            assert sorted(params.keys()) == ['_columns', '_fields', '_results_number', 'uuid']

            return {
                'hits': [{'uuid': uuid} for uuid in uuids],
                'facets': {
                    'signature': []
                },
                'total': len(uuids)
            }

        with mock.patch('crashstats.supersearch.models.SuperSearch.implementation') as mock_ss:
            mock_ss.return_value.get.side_effect = mocked_supersearch_get
            yield

    def test_bad_uuid(self, client):
        url = reverse('api:crash_verify')

        resp = client.get(url, {'crash_id': 'foo'})
        assert resp.status_code == 400
        data = json.loads(resp.content)
        assert data == {'error': 'unknown crash id'}

    @mock_s3_deprecated
    def test_elastcsearch_has_crash(self, client):
        uuid = create_new_ooid()

        with self.supersearch_returns_crashes([uuid]):
            url = reverse('api:crash_verify')
            resp = client.get(url, {'crash_id': uuid})

        assert resp.status_code == 200
        data = json.loads(resp.content)

        assert (
            data ==
            {
                u'uuid': uuid,
                u'elasticsearch_crash': True,

                u's3_raw_crash': False,
                u's3_processed_crash': False,
                u's3_telemetry_crash': False,
            }
        )

    @mock_s3_deprecated
    def test_raw_crash_has_crash(self, client):
        uuid = create_new_ooid()
        crash_data = {
            'submitted_timestamp': '2018-03-14-09T22:21:18.646733+00:00'
        }

        boto_helper = BotoHelper()
        raw_crash_key = '/v2/raw_crash/%s/20%s/%s' % (uuid[0:3], uuid[-6:], uuid)
        boto_helper.get_or_create_bucket('crashstats-test')
        boto_helper.set_contents_from_string(
            bucket_name='crashstats-test',
            key=raw_crash_key,
            value=json.dumps(crash_data)
        )

        with self.supersearch_returns_crashes([]):
            url = reverse('api:crash_verify')
            resp = client.get(url, {'crash_id': uuid})

        assert resp.status_code == 200
        data = json.loads(resp.content)

        assert (
            data ==
            {
                u'uuid': uuid,
                u's3_raw_crash': True,

                u's3_processed_crash': False,
                u'elasticsearch_crash': False,
                u's3_telemetry_crash': False,
            }
        )

    @mock_s3_deprecated
    def test_processed_has_crash(self, client):
        uuid = create_new_ooid()
        crash_data = {
            'signature': '[@signature]',
            'uuid': uuid,
            'completeddatetime': '2018-03-14 10:56:50.902884',
        }

        boto_helper = BotoHelper()
        boto_helper.get_or_create_bucket('crashstats-test')
        boto_helper.set_contents_from_string(
            bucket_name='crashstats-test',
            key='/v1/processed_crash/%s' % uuid,
            value=json.dumps(crash_data)
        )

        with self.supersearch_returns_crashes([]):
            url = reverse('api:crash_verify')
            resp = client.get(url, {'crash_id': uuid})

        assert resp.status_code == 200
        data = json.loads(resp.content)

        assert (
            data ==
            {
                u'uuid': uuid,
                u's3_processed_crash': True,

                u's3_raw_crash': False,
                u'elasticsearch_crash': False,
                u's3_telemetry_crash': False,
            }
        )

    @mock_s3_deprecated
    def test_telemetry_has_crash(self, client):
        uuid = create_new_ooid()
        crash_data = {
            'platform': 'Linux',
            'signature': 'now_this_is_a_signature',
            'uuid': uuid
        }

        boto_helper = BotoHelper()
        boto_helper.get_or_create_bucket('telemetry-test')
        boto_helper.set_contents_from_string(
            bucket_name='telemetry-test',
            key='/v1/crash_report/20%s/%s' % (uuid[-6:], uuid),
            value=json.dumps(crash_data)
        )

        with self.supersearch_returns_crashes([]):
            url = reverse('api:crash_verify')
            resp = client.get(url, {'crash_id': uuid})

        assert resp.status_code == 200
        data = json.loads(resp.content)

        assert (
            data ==
            {
                u'uuid': uuid,
                u's3_telemetry_crash': True,

                u's3_raw_crash': False,
                u's3_processed_crash': False,
                u'elasticsearch_crash': False,
            }
        )


class TestVersionString(object):
    @contextlib.contextmanager
    def mock_VersionString(self, results):
        with mock.patch('crashstats.crashstats.models.VersionString.implementation') as mock_i:
            mock_i.return_value.get.return_value = {
                'hits': results
            }
            yield
        SocorroCommon.clear_implementations_cache()
        cache.clear()

    def test_version_string_no_args(self, client):
        url = reverse('api:model_wrapper', args=('VersionString',))
        response = client.get(url)
        # Sending in no args is an HTTP 400
        assert response.status_code == 400

    def test_version_string_args(self, client):
        with self.mock_VersionString(['62.0b4']):
            url = reverse('api:model_wrapper', args=('VersionString',))
            response = client.get(url, {
                'product': 'Test',
                'version': '62.0',
                'build_id': '20180816151750'
            })
            assert response.status_code == 200
            assert json.loads(response.content) == {'hits': ['62.0b4']}

    def test_version_string_args_no_valid_version(self, client):
        with self.mock_VersionString([]):
            url = reverse('api:model_wrapper', args=('VersionString',))
            response = client.get(url, {
                'product': 'Test',
                'version': '62.0',
                'build_id': '20180816151750'
            })
            assert response.status_code == 200
            assert json.loads(response.content) == {'hits': []}
