import datetime
import re
import json
import unittest

from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_, ok_
from waffle import Switch

from crashstats.crashstats.tests.test_views import (
    BaseTestViews,
    Response
)


class TestDedentLeft(unittest.TestCase):

    def test_dedent_left(self):
        from crashstats.api.views import dedent_left
        eq_(dedent_left('Hello', 2), 'Hello')
        eq_(dedent_left('   Hello', 2), ' Hello')
        eq_(dedent_left('   Hello ', 2), ' Hello ')

        text = """Line 1
        Line 2
        Line 3
        """.rstrip()
        # because this code right above is indented with 2 * 4 spaces
        eq_(dedent_left(text, 8), 'Line 1\nLine 2\nLine 3')


class TestDocumentationViews(BaseTestViews):

    @staticmethod
    def setUpClass():
        TestDocumentationViews.switch = Switch.objects.create(
            name='app_api_all',
            active=True,
        )

    @staticmethod
    def tearDownClass():
        TestDocumentationViews.switch.delete()

    def test_documentation_home_page(self):
        url = reverse('api:documentation')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        from crashstats.api import views
        for each in views.BLACKLIST:
            ok_(each not in response.content)


class TestViews(BaseTestViews):

    @staticmethod
    def setUpClass():
        TestViews.switch = Switch.objects.create(
            name='app_api_all',
            active=True,
        )

    @staticmethod
    def tearDownClass():
        TestViews.switch.delete()

    def test_invalid_url(self):
        url = reverse('api:model_wrapper', args=('BlaBLabla',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

    @mock.patch('requests.get')
    def test_CrashesPerAdu(self, rget):
        def mocked_get(url, **options):
            if 'crashes/daily' in url:
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

        url = reverse('api:model_wrapper', args=('CrashesPerAdu',))
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'versions': ['10.0', '11.1'],
        })
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/json; charset=UTF-8')
        dump = json.loads(response.content)
        ok_(dump['hits'])

        # miss one of the required fields
        response = self.client.get(url, {
            # note! no 'product'
            'versions': ['10.0', '11.1'],
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['product'])
        ok_('versions' not in dump['errors'])

    @mock.patch('requests.get')
    def test_CORS(self, rget):
        """any use of model_wrapper should return a CORS header"""

        def mocked_get(url, **options):
            return Response("""
                {
                  "breakpad_revision": "1139",
                  "hits": [
                    {
                      "date_oldest_job_queued": null,
                      "date_recently_completed": null,
                      "processors_count": 1,
                      "avg_wait_sec": 0.0,
                      "waiting_job_count": 0,
                      "date_created": "2013-04-01T21:40:01+00:00",
                      "id": 463859,
                      "avg_process_sec": 0.0
                    }
                  ],
                  "total": 12,
                  "socorro_revision": "9cfa4de"
                }
            """)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('Status',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Access-Control-Allow-Origin'], '*')

    @mock.patch('requests.get')
    def test_CrashesPerAdu_too_much(self, rget):
        def mocked_get(url, **options):
            if 'crashes/daily' in url:
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
        url = reverse('api:model_wrapper', args=('CrashesPerAdu',))
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'versions': ['10.0', '11.1'],
        })
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/json; charset=UTF-8')
        for i in range(5):
            response = self.client.get(url, {
                'product': 'WaterWolf',
                'versions': ['10.0', '11.1'],
            })
        # should still be ok
        eq_(response.status_code, 200)

        for i in range(1001):
            response = self.client.get(url, {
                'product': 'WaterWolf',
                'versions': ['10.0', '11.1'],
            })
        eq_(response.status_code, 429)
        eq_(response.content, 'Too Many Requests')

    @mock.patch('requests.get')
    def test_CrashesPerAdu_different_date_parameters(self, rget):
        def mocked_get(url, **options):
            if 'crashes/daily' in url:
                # note that the test below sends in a string as
                # '2012-1-1' which is valid but lacks the leading
                # zeros. Because the date is converted to a datetime.date
                # object and serialized back we'll get it here in this
                # full format.
                ok_('from_date/2012-01-01' in url)
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

        url = reverse('api:model_wrapper', args=('CrashesPerAdu',))
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'versions': ['10.0', '11.1'],
            'from_date': '2012-01-xx',  # invalid format
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['from_date'])

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'versions': ['10.0', '11.1'],
            'from_date': '2012-02-32',  # invalid numbers
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['from_date'])

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'versions': ['10.0', '11.1'],
            'from_date': '2012-1-1',
        })
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_CurrentVersions(self, rget):
        url = reverse('api:model_wrapper', args=('CurrentVersions',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(isinstance(dump, list))
        first = dump[0]
        ok_('product' in first)

    @mock.patch('requests.get')
    def test_CurrentProducts(self, rget):
        url = reverse('api:model_wrapper', args=('CurrentProducts',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        ok_(dump['products'])
        ok_(dump['total'])

    @mock.patch('requests.get')
    def test_ProductsVersions(self, rget):
        url = reverse('api:model_wrapper', args=('ProductsVersions',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_('WaterWolf' in dump)
        ok_('NightTrain' in dump)
        versions = dump['WaterWolf']
        version = versions[0]
        ok_('product' in version)
        ok_('version' in version)
        ok_('throttle' in version)
        ok_('start_date' in version)
        ok_('end_date' in version)
        ok_('featured' in version)
        ok_('release' in version)

    @mock.patch('requests.get')
    def test_Platforms(self, rget):
        url = reverse('api:model_wrapper', args=('Platforms',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump[0]['code'])
        ok_(dump[0]['name'])

    @mock.patch('requests.get')
    def test_TCBS(self, rget):

        def mocked_get(url, **options):
            if 'crashes/signatures' in url:
                # because it defaults to insert a `limit` we should see
                # that somewhere in the URL
                ok_(re.findall('limit/\d+', url))
                ok_('/os/' not in url)
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
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('TCBS',))
        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '19.0a2',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['crashes'])

    @mock.patch('requests.get')
    def test_TCBS_with_optional_parameters(self, rget):

        def mocked_get(url, **options):
            if 'crashes/signatures' in url:
                ok_('limit/100/' in url)
                ok_('/os/OSX/' in url)
                ok_('end_date/2013-01-01/' in url)
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

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('TCBS',))
        data = {
            'product': 'WaterWolf',
            'version': '19.0a2',
            'limit': 'xxx',
            'duration': 'yyy',
            'end_date': 'zzz',
            'os': 'OSX',
        }
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['limit'])
        ok_(dump['errors']['duration'])
        ok_(dump['errors']['end_date'])

        data['limit'] = '100'
        data['duration'] = '1'
        data['end_date'] = '2013-1-1'
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['crashes'])

    @mock.patch('requests.get')
    def test_ReportList(self, rget):
        url = reverse('api:model_wrapper', args=('ReportList',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['signature'])

        def mocked_get(url, **options):
            if 'report/list/' in url:
                ok_('signature/one%20%26%20' in url)
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "address": "0xdeadbeef"
                    },
                    {
                      "user_comments": null,
                      "address": "0xdeadbeef"
                    }
                    ],
                    "total": 2
                    }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'signature': 'one & two',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['start_date'])
        ok_(dump['errors']['end_date'])

        now = datetime.datetime.utcnow()
        yesterday = now - datetime.timedelta(days=1)
        fmt = lambda x: x.strftime('%Y-%m-%d %H:%M:%S')
        response = self.client.get(url, {
            'signature': 'one & two',
            'start_date': fmt(yesterday),
            'end_date': fmt(now),
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        ok_(dump['total'])

    @mock.patch('requests.get')
    def test_ReportList_with_optional_parameters(self, rget):
        url = reverse('api:model_wrapper', args=('ReportList',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['signature'])

        def mocked_get(url, **options):
            if 'report/list/' in url:
                ok_('products/WaterWolf%2BNightTrain/' in url)
                ok_('versions/11%2B12/' in url)
                ok_('build_ids/XYZ/' in url)
                ok_('signature/one%20%26%20two/' in url)
                ok_('os/OSX%2BWINDOWS/' in url)
                ok_('from/2012-01-01T00%3A00%3A00' in url)
                ok_('to/2013-01-01T00%3A00%3A00' in url)
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "address": "0xdeadbeef"
                    },
                    {
                      "user_comments": null,
                      "address": "0xdeadbeef"
                    }
                    ],
                    "total": 2
                    }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'signature': 'one & two',
            'products': ['WaterWolf', 'NightTrain'],
            'versions': ['11', '12'],
            'os': ['OSX', 'WINDOWS'],
            'range_value': '100',
            'start_date': '2012-1-1',
            'end_date': '2013-1-1',
            'build_ids': 'XYZ',
            'reasons': 'Anger',
            'release_channels': 'noideawhatthisdoes',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        ok_(dump['total'])

    @mock.patch('requests.get')
    def test_ProcessedCrash(self, rget):
        url = reverse('api:model_wrapper', args=('ProcessedCrash',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['crash_id'])

        def mocked_get(url, **options):
            assert '/crash_data/' in url
            if '/datatype/processed' in url:
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
                  "success": true
                }
                """ % dump)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'crash_id': '123',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        eq_(dump['uuid'], u'11cb72f5-eb28-41e1-a8e4-849982120611')

    @mock.patch('requests.get')
    def test_RawCrash(self, rget):

        def mocked_get(url, **options):
            if 'crash_data/uuid/abc123' in url:
                return Response("""
            {
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
            "Add-ons": "activities%40gaiamobile.org:0.1,alarms%40gaiam...",
            "BuildID": "20130422105838",
            "SecondsSinceLastCrash": "23484",
            "ProductName": "WaterWolf",
            "legacy_processing": 0,
            "ProductID": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
            "AsyncShutdownTimeout": 12345,
            "BIOS_Manufacturer": "abc123",
            "Comments": "I visited http://p0rn.com and mail@email.com",
            "upload_file_minidump_browser": "a crash",
            "upload_file_minidump_flash1": "a crash",
            "upload_file_minidump_flash2": "a crash",
            "upload_file_minidump_plugin": "a crash",
            "upload_file_minidump_not_known_about": "a crash"
            }
            """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('RawCrash',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['crash_id'])

        response = self.client.get(url, {
            'crash_id': 'abc123'
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_('id' in dump)
        ok_('URL' not in dump)  # right?
        ok_('AsyncShutdownTimeout' in dump)
        ok_('BIOS_Manufacturer' in dump)
        ok_('upload_file_minidump_browser' in dump)
        ok_('upload_file_minidump_flash1' in dump)
        ok_('upload_file_minidump_flash2' in dump)
        ok_('upload_file_minidump_plugin' in dump)
        ok_('upload_file_minidump_not_known_about' not in dump)

        # `Comments` is scrubbed
        ok_('I visited' in dump['Comments'])
        ok_('http://p0rn.com' not in dump['Comments'])
        ok_('mail@email.com' not in dump['Comments'])

    @mock.patch('requests.get')
    def test_RawCrash_binary_blob(self, rget):

        def mocked_get(url, **options):
            if 'crash_data/uuid/abc' in url:
                return Response('\xe0')
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('RawCrash',))
        response = self.client.get(url, {
            'crash_id': 'abc'
        })
        eq_(response.status_code, 400)

    @mock.patch('requests.get')
    def test_CommentsBySignature(self, rget):
        url = reverse('api:model_wrapper', args=('CommentsBySignature',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['signature'])

        def mocked_get(url, **options):
            if 'crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "This is a comment",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "some@emailaddress.com",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'signature': 'one & two',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        ok_(dump['total'])

    @mock.patch('requests.get')
    def test_CrashPairsByCrashId(self, rget):
        url = reverse('api:model_wrapper', args=('CrashPairsByCrashId',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['uuid'])
        ok_(dump['errors']['hang_id'])

        def mocked_get(url, **options):
            return Response("""
              {
                "hits": [{"guess": "work"}],
                "total": 1
              }
            """)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'uuid': '123',
            'hang_id': '987'
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        ok_(dump['total'])

    @mock.patch('requests.get')
    def test_Search(self, rget):

        def mocked_get(url, **options):
            assert 'search/signatures' in url
            if 'products/WaterWolf' in url:
                ok_('signatures/for/ABC123' in url)
                ok_('products/WaterWolf%2BNightTrain' in url)
                ok_('versions/19.0%2B18.0' in url)
                ok_('os/OSX%2BWin95/' in url)

                return Response("""{
                    "hits": [
                    {
                      "count": 586,
                      "signature": "nsASDOMWindowEnumerator::GetNext()",
                      "numcontent": 0,
                      "is_windows": 586,
                      "is_linux": 0,
                      "numplugin": 56,
                      "is_mac": 0,
                      "numhang": 0
                    },
                    {
                      "count": 13,
                      "signature": "mySignatureIsCool",
                      "numcontent": 0,
                      "is_windows": 10,
                      "is_linux": 2,
                      "numplugin": 0,
                      "is_mac": 1,
                      "numhang": 0
                    },
                    {
                      "count": 2,
                      "signature": "mineIsCoolerThanYours",
                      "numcontent": 0,
                      "is_windows": 0,
                      "is_linux": 0,
                      "numplugin": 0,
                      "is_mac": 2,
                      "numhang": 2
                    },
                    {
                      "count": 2,
                      "signature": null,
                      "numcontent": 0,
                      "is_windows": 0,
                      "is_linux": 0,
                      "numplugin": 0,
                      "is_mac": 2,
                      "numhang": 2
                    }
                    ],
                    "total": 4
                } """)
            else:
                return Response("""
                {"hits": [
                      {
                      "count": 586,
                      "signature": "nsASDOMWindowEnumerator::GetNext()",
                      "numcontent": 0,
                      "is_windows": 586,
                      "is_linux": 0,
                      "numplugin": 0,
                      "is_mac": 0,
                      "numhang": 0
                    }],
                  "total": 1
                  }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('Search',))
        response = self.client.get(url, {
            'terms': 'ABC123',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        eq_(dump['total'], 1)

        response = self.client.get(url, {
            'terms': 'ABC123',
            'products': ['WaterWolf', 'NightTrain'],
            'versions': ['19.0', '18.0'],
            'os': ['OSX', 'Win95'],
            'start_date': '2012-1-1 23:00:00',
            'end_date': '2013-1-1 23:00:00',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        eq_(dump['total'], 4)

    @mock.patch('requests.post')
    def test_Bugs(self, rpost):
        url = reverse('api:model_wrapper', args=('Bugs',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['signatures'])

        def mocked_post(**options):
            assert '/bugs/' in options['url'], options['url']
            return Response("""
               {"hits": [{"id": "123456789",
                          "signature": "Something"}]}
            """)
        rpost.side_effect = mocked_post

        response = self.client.get(url, {
            'signatures': 'one & two',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])

    @mock.patch('requests.post')
    def test_SignaturesForBugs(self, rpost):
        url = reverse('api:model_wrapper', args=('SignaturesByBugs',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['bug_ids'])

        def mocked_post(**options):
            assert '/bugs/' in options['url'], options['url']
            return Response("""
               {"hits": [{"id": "123456789",
                          "signature": "Something"}]}
            """)
        rpost.side_effect = mocked_post

        response = self.client.get(url, {
            'bug_ids': '123456789',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])

    @mock.patch('requests.get')
    def test_SignatureTrend(self, rget):

        def mocked_get(url, **options):
            if 'crashes/signature_history' in url:
                ok_('product/WaterWolf/' in url)
                ok_('version/19.0/' in url)
                ok_('end_date/2013-01-01/' in url)
                ok_('start_date/2012-01-01/' in url)
                ok_('signature/one%20%26%20two/' in url)

                return Response("""
                {
                    "hits": [
                        {
                            "count": 1,
                            "date": "2012-06-06",
                            "percent_of_total": 100
                        }
                    ],
                    "total": 1
                }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('SignatureTrend',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['product'])
        ok_(dump['errors']['version'])
        ok_(dump['errors']['signature'])
        ok_(dump['errors']['end_date'])
        ok_(dump['errors']['start_date'])

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '19.0',
            'signature': 'one & two',
            'end_date': '2013-1-1',
            'start_date': '2012-1-1',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        ok_(dump['total'])

    @mock.patch('requests.get')
    def test_SignatureSummary(self, rget):

        def mocked_get(url, **options):
            if 'signaturesummary' in url:
                ok_('/report_type/uptime/' in url)
                ok_('/signature/one%20%26%20two/' in url)
                ok_('/start_date/2012-01-01/' in url)
                ok_('/end_date/2013-01-01/' in url)
                return Response("""
                [
                  {
                    "version_string": "12.0",
                    "percentage": "48.440",
                    "report_count": 52311,
                    "product_name": "WaterWolf",
                    "category": "XXX"
                  },
                  {
                    "version_string": "13.0b4",
                    "percentage": "9.244",
                    "report_count": 9983,
                    "product_name": "WaterWolf",
                    "category": "YYY"
                  }
                ]
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('SignatureSummary',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['start_date'])
        ok_(dump['errors']['end_date'])
        ok_(dump['errors']['report_type'])
        ok_(dump['errors']['signature'])

        response = self.client.get(url, {
            'report_type': 'uptime',
            'signature': 'one & two',
            'start_date': '2012-1-1',
            'end_date': '2013-1-1',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump)
        eq_(len(dump), 2)

    @mock.patch('requests.get')
    def test_Status(self, rget):

        def mocked_get(url, **options):

            if 'server_status/' in url:
                return Response("""
                {
                  "breakpad_revision": "1139",
                  "hits": [
                    {
                      "date_oldest_job_queued": null,
                      "date_recently_completed": null,
                      "processors_count": 1,
                      "avg_wait_sec": 0.0,
                      "waiting_job_count": 0,
                      "date_created": "2013-04-01T21:40:01+00:00",
                      "id": 463859,
                      "avg_process_sec": 0.0
                    }
                  ],
                  "total": 12,
                  "socorro_revision": "9cfa4de"
                }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('Status',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        ok_(dump['socorro_revision'])

    @mock.patch('requests.get')
    def test_CrontabberState(self, rget):

        def mocked_get(url, **options):
            if '/crontabber_state/' in url:
                return Response("""
                {
                  "state": {
                    "automatic-emails": {
                      "next_run": "2013-04-01 22:20:01.736562",
                      "first_run": "2013-03-15 16:25:01.411345",
                      "depends_on": [],
                      "last_run": "2013-04-01 21:20:01.736562",
                      "last_success": "2013-04-01 20:25:01.411369",
                      "error_count": 0,
                      "last_error": {}
                    },
                    "ftpscraper": {
                      "next_run": "2013-04-01 22:20:09.909384",
                      "first_run": "2013-03-07 07:05:51.650177",
                      "depends_on": [],
                      "last_run": "2013-04-01 21:20:09.909384",
                      "last_success": "2013-04-01 21:05:51.650191",
                      "error_count": 0,
                      "last_error": {}
                    }
                  },
                  "last_updated": "2013-04-01T21:45:02+00:00"
                }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('CrontabberState',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['state'])
        ok_(dump['last_updated'])

    @mock.patch('requests.get')
    def test_DailyBuilds(self, rget):
        def mocked_get(url, **options):
            if '/products/builds/' in url:
                return Response("""
                    [
                      {
                        "product": "WaterWolf",
                        "repository": "dev",
                        "buildid": 20120625000001,
                        "beta_number": null,
                        "platform": "Mac OS X",
                        "version": "19.0",
                        "date": "2012-06-25",
                        "build_type": "Nightly"
                      },
                      {
                        "product": "WaterWolf",
                        "repository": "dev",
                        "buildid": 20120625000003,
                        "beta_number": null,
                        "platform": "BeOS",
                        "version": "5.0a1",
                        "date": "2012-06-25",
                        "build_type": "Beta"
                      }
                    ]
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('DailyBuilds',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['product'])

        response = self.client.get(url, {
            'product': 'WaterWolf',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump)
        ok_(dump[0]['buildid'])

    @mock.patch('requests.get')
    def test_CrashTrends(self, rget):
        def mocked_get(url, **options):
            if '/crashtrends/' in url:
                ok_('/product/WaterWolf/' in url)
                ok_('/version/5.0/' in url)
                ok_('/start_date/2012-01-01/' in url)
                ok_('/end_date/2013-01-01/' in url)
                return Response("""
                {
                  "crashtrends": [
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

        url = reverse('api:model_wrapper', args=('CrashTrends',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['product'])
        ok_(dump['errors']['version'])
        ok_(dump['errors']['start_date'])
        ok_(dump['errors']['end_date'])

        response = self.client.get(url, {
            'product': 'WaterWolf',
            'version': '5.0',
            'start_date': '2012-1-1',
            'end_date': '2013-1-1',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['crashtrends'])
        ok_(dump['total'])

    @mock.patch('requests.get')
    def test_SignatureURLs(self, rget):
        def mocked_get(url, **options):
            if '/signatureurls/' in url:
                ok_('/products/WaterWolf%2BNightTrain/' in url)
                ok_('/start_date/2012-01-01T10%3A00%3A00/' in url)
                ok_('/end_date/2013-01-01T10%3A00%3A00/' in url)
                return Response("""{
                    "hits": [
                        {"url": "http://farm.ville", "crash_count":123},
                        {"url": "http://other.crap", "crash_count": 1}
                    ],
                    "total": 2
                }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('SignatureURLs',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['errors']['products'])
        ok_(dump['errors']['signature'])
        ok_(dump['errors']['start_date'])
        ok_(dump['errors']['end_date'])

        response = self.client.get(url, {
            'products': ['WaterWolf', 'NightTrain'],
            'versions': ['WaterWolf:14.0', 'NightTrain:15.0'],
            'start_date': '2012-1-1 10:00:0',
            'end_date': '2013-1-1 10:00:0',
            'signature': 'one & two',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        ok_(dump['hits'])
        ok_(dump['total'])

    @mock.patch('requests.get')
    def test_carry_mware_error_codes(self, rget):

        # used so we can count, outside the mocked function,
        # how many times the `requests.get` is called
        attempts = []

        def mocked_get(url, **options):
            attempts.append(url)
            if len(attempts) == 1:
                return Response('Not found Stuff', status_code=400)
            if len(attempts) == 2:
                return Response('Forbidden Stuff', status_code=403)
            if len(attempts) == 3:
                return Response('Bad Stuff', status_code=500)
            if len(attempts) == 4:
                return Response('Someone elses Bad Stuff', status_code=502)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('CrontabberState',))
        response = self.client.get(url)
        eq_(response.status_code, 400)
        # second attempt
        response = self.client.get(url)
        eq_(response.status_code, 403)
        # third attempt
        response = self.client.get(url)
        eq_(response.status_code, 424)
        # forth attempt
        response = self.client.get(url)
        eq_(response.status_code, 424)

    @mock.patch('requests.get')
    def test_Correlations(self, rget):

        def mocked_get(url, **options):
            assert 'correlations/report_type' in url
            return Response("""
                {
                    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                    "count": 13,
                    "load": "36% (4/11) vs.  26% (47/180) amd64 with 2 cores"
                }
            """)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('Correlations',))
        response = self.client.get(url)
        dump = json.loads(response.content)
        ok_(dump['errors']['product'])
        ok_(dump['errors']['platform'])
        ok_(dump['errors']['version'])
        ok_(dump['errors']['report_type'])
        ok_(dump['errors']['signature'])

        response = self.client.get(url, {
            'platform': 'Windows NT',
            'product': 'WaterWolf',
            'version': '1.0',
            'report_type': 'core-counts',
            'signature': 'one & two',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        eq_(dump['count'], 13)
        eq_(dump['reason'], 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS')
        ok_(dump['load'])

    @mock.patch('requests.get')
    def test_CorrelationsSignatures(self, rget):

        def mocked_get(url, **options):
            assert 'correlations/signatures' in url
            return Response("""
                {
                    "hits": ["FakeSignature1",
                             "FakeSignature2"],
                    "total": 2
                }
            """)

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('CorrelationsSignatures',))
        response = self.client.get(url)
        dump = json.loads(response.content)
        ok_(dump['errors']['product'])
        ok_(dump['errors']['version'])
        ok_(dump['errors']['report_type'])

        response = self.client.get(url, {
            'platforms': 'Windows NT+Mac OS OX',
            'product': 'WaterWolf',
            'version': '1.0',
            'report_type': 'core-counts',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        eq_(dump['hits'], [u'FakeSignature1', u'FakeSignature2'])
        eq_(dump['total'], 2)

    def test_Field(self):
        url = reverse('api:model_wrapper', args=('Field',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

    @mock.patch('requests.get')
    def test_Correlations_returning_nothing(self, rget):

        def mocked_get(url, **options):
            assert 'correlations/report_type' in url
            # 'null' is a perfectly valid JSON response
            return Response('null')

        rget.side_effect = mocked_get

        url = reverse('api:model_wrapper', args=('Correlations',))
        response = self.client.get(url, {
            'platform': 'Windows NT',
            'product': 'WaterWolf',
            'version': '1.0',
            'report_type': 'core-counts',
            'signature': 'one & two',
        })
        eq_(response.status_code, 200)
        dump = json.loads(response.content)
        eq_(dump, None)
