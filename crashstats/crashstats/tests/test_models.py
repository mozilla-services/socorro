import json
import os
import shutil
import tempfile
import datetime
import time
import mock
from nose.tools import eq_, ok_
from django.test import TestCase
from django.core.cache import cache
from django.conf import settings
from crashstats.crashstats import models


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


class TestModels(TestCase):

    def setUp(self):
        super(TestModels, self).setUp()
        # thanks to settings_test.py
        assert settings.CACHE_MIDDLEWARE
        assert not settings.CACHE_MIDDLEWARE_FILES
        cache.clear()

    def tearDown(self):
        super(TestModels, self).tearDown()

    @mock.patch('requests.get')
    def test_bugzilla_api(self, rget):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(**options):
            assert options['url'].startswith(models.BugzillaAPI.base_url)
            return Response('{"bugs": [{"product": "mozilla.org"}]}')

        rget.side_effect = mocked_get
        info = api.get('747237', 'product')
        eq_(info['bugs'], [{u'product': u'mozilla.org'}])

        # prove that it's cached by default
        def new_mocked_get(**options):
            return Response('{"bugs": [{"product": "DIFFERENT"}]}')

        rget.side_effect = new_mocked_get
        info = api.get('747237', 'product')
        eq_(info['bugs'], [{u'product': u'mozilla.org'}])

        info = api.get('747238', 'product')
        eq_(info['bugs'], [{u'product': u'DIFFERENT'}])

    @mock.patch('requests.get')
    def test_current_versions(self, rget):
        model = models.CurrentVersions
        api = model()

        def mocked_get(**options):
            assert 'current/versions/' in options['url']
            return Response("""
                {"currentversions": [{
                  "product": "Camino",
                  "throttle": "100.00",
                  "end_date": "2012-05-10 00:00:00",
                  "start_date": "2012-03-08 00:00:00",
                  "featured": true,
                  "version": "2.1.3pre",
                  "release": "Beta",
                  "id": 922}]
                  }
              """)

        rget.side_effect = mocked_get
        info = api.get()
        ok_(isinstance(info, list))
        ok_(isinstance(info[0], dict))
        eq_(info[0]['product'], 'Camino')

    @mock.patch('requests.get')
    def test_crashes(self, rget):
        model = models.Crashes
        api = model()

        def mocked_get(**options):
            assert 'crashes' in options['url']
            return Response("""
               {"product": "Thunderbird",
                "start_date": "2012-05-29 00:00:00+00:00",
                "end_date": "2012-05-30 00:00:00+00:00",
                "versions": [{"statistics": [], "version": "12.0"}]
                }
              """)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        yesterday = today - datetime.timedelta(days=1)
        r = api.get('Thunderbird', ['12.0'], ['Mac'], yesterday, today)
        eq_(r['product'], 'Thunderbird')
        ok_(r['versions'])

    @mock.patch('requests.get')
    def test_tcbs(self, rget):
        model = models.TCBS
        api = model()

        def mocked_get(**options):
            assert 'crashes/signatures' in options['url']
            return Response("""
               {"crashes": [],
                "totalPercentage": 0,
                "start_date": "2012-05-10",
                "end_date": "2012-05-24",
                "totalNumberOfCrashes": 0}
              """)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        r = api.get('Thunderbird', '12.0', 'plugin', today, 336)
        eq_(r['crashes'], [])

    @mock.patch('requests.get')
    def test_report_list(self, rget):
        model = models.ReportList
        api = model()

        def mocked_get(**options):
            assert 'report/list/signature' in options['url']
            return Response("""
                {
          "hits": [
            {
              "product": "Fennec",
              "os_name": "Linux",
              "uuid": "5e30f10f-cd5d-4b13-9dbc-1d1e62120524",
              "many_others": "snipped out"
            }],
          "total": 333
          }
              """)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        r = api.get('Pickle::ReadBytes', 'Fennec', today, 250, 0)
        ok_(r['total'])
        ok_(r['hits'])

    @mock.patch('requests.get')
    def test_hangreport(self, rget):
        model = models.HangReport
        api = model()

        def mocked_get(**options):
            assert 'reports/hang/' in options['url']
            return Response("""
                {"currentPage": 1,
                 "endDate": "2012-06-01 00:00:00+00:00",
                 "hangReport": [{
                   "browser_hangid": "30a712a4-6512-479d-9a0a-48b4d8c7ca13",
                   "browser_signature": "hang | mozilla::plugins::",
                   "duplicates": [
                     null,
                     null,
                     null
                   ],
                   "flash_version": "11.3.300.250",
                   "plugin_signature": "hang | ZwYieldExecution",
                   "report_day": "2012-05-31",
                   "url": "http://example.com",
                   "uuid": "176bcd6c-c2ec-4b0c-9d5f-dadea2120531"
                   }],
                 "totalCount": 1,
                 "totalPages": 0}
              """)

        rget.side_effect = mocked_get
        r = api.get(product='Firefox', version='15.0a1',
                    end_date='2012-06-01', duration=(7 * 24),
                    listsize=300, page=1)

        eq_(
            r['hangReport'],
            [{u'uuid': u'176bcd6c-c2ec-4b0c-9d5f-dadea2120531',
              u'flash_version': u'11.3.300.250',
              u'duplicates': [None, None, None],
              u'url': u'http://example.com',
              u'report_day':  u'2012-05-31',
              u'plugin_signature': u'hang | ZwYieldExecution',
              u'browser_hangid': u'30a712a4-6512-479d-9a0a-48b4d8c7ca13',
              u'browser_signature': 'hang | mozilla::plugins::',
              }]
        )

    @mock.patch('requests.get')
    def test_report_index(self, rget):
        model = models.ProcessedCrash
        api = model()

        def mocked_get(**options):
            assert 'crash/processed' in options['url'], options['url']
            return Response("""
            {
              "product": "Firefox",
              "uuid": "7c44ade2-fdeb-4d6c-830a-07d302120525",
              "version": "13.0",
              "build": "20120501201020",
              "ReleaseChannel": "beta",
              "os_name": "Windows NT",
              "date_processed": "2012-05-25 11:35:57.446995",
              "success": true,
              "signature": "CLocalEndpointEnumerator::OnMediaNotific",
              "addons": [
                [
                  "testpilot@labs.mozilla.com",
                  "1.2.1"
                ],
                [
                  "{972ce4c6-7e08-4474-a285-3208198ce6fd}",
                  "13.0"
                ]
              ]
            }
            """)

        rget.side_effect = mocked_get
        r = api.get('7c44ade2-fdeb-4d6c-830a-07d302120525')
        ok_(r['product'])

    @mock.patch('requests.get')
    def test_search(self, rget):
        model = models.Search
        api = model()

        def mocked_get(**options):
            assert 'search/signatures' in options['url'], options['url']
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
              "total": 123
              }
            """)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        yesterday = today - datetime.timedelta(days=10)
        r = api.get('Thunderbird', '12.0', 'Mac', yesterday, today, 100)
        ok_(r['hits'])
        ok_(r['total'])

    @mock.patch('requests.post')
    def test_bugs(self, rpost):
        model = models.Bugs
        api = model()

        def mocked_post(**options):
            assert '/bugs/' in options['url'], options['url']
            assert options['data'] == {'signatures': 'Pickle::ReadBytes'}
            return Response('{"hits": ["123456789"]}')

        rpost.side_effect = mocked_post
        r = api.get('Pickle::ReadBytes')
        ok_(r['hits'])

    @mock.patch('requests.get')
    def test_signature_trend(self, rget):
        model = models.SignatureTrend
        api = model()

        def mocked_get(**options):
            assert 'topcrash/sig/trend' in options['url'], options['url']
            return Response("""
            {
              "signature": "Pickle::ReadBytes",
              "start_date": "2012-04-19T08:00:00+00:00",
              "end_date": "2012-05-31T00:00:00+00:00",
              "signatureHistory": []
            }
            """)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        r = api.get('Thunderbird', '12.0', 'Pickle::ReadBytes',
                    today, 1000)
        ok_(r['signature'])

    @mock.patch('requests.get')
    def test_signature_summary(self, rget):
        model = models.SignatureSummary
        api = model()

        def mocked_get(**options):
            assert 'signaturesummary' in options['url'], options['url']
            return Response("""
            [
              {
                "version_string": "12.0",
                "percentage": "48.440",
                "report_count": 52311,
                "product_name": "Firefox"
              },
              {
                "version_string": "13.0b4",
                "percentage": "9.244",
                "report_count": 9983,
                "product_name": "Firefox"
              }
            ]
            """)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        yesterday = today - datetime.timedelta(days=10)
        r = api.get('products', 'Pickle::ReadBytes', yesterday, today)
        ok_(r[0]['version_string'])

    @mock.patch('requests.get')
    def test_status(self, rget):
        def mocked_get(**options):
            assert 'status' in options['url'], options['url']
            return Response("""
                {
                    "breakpad_revision": "1035",
                    "hits": [
                        {
                            "date_oldest_job_queued":
                                "2012-09-28T20:39:33.688881+00:00",
                            "date_recently_completed":
                                "2012-09-28T20:40:00.033047+00:00",
                            "processors_count": 1,
                            "avg_wait_sec": 16.407,
                            "waiting_job_count": 56,
                            "date_created": "2012-09-28T20:40:02.032575+00:00",
                            "id": 410655,
                            "avg_process_sec": 0.914149
                        },
                        {
                            "date_oldest_job_queued":
                                "2012-09-28T20:34:33.101709+00:00",
                            "date_recently_completed":
                                "2012-09-28T20:35:00.821435+00:00",
                            "processors_count": 1,
                            "avg_wait_sec": 13.8293,
                            "waiting_job_count": 48,
                            "date_created": "2012-09-28T20:35:01.834452+00:00",
                            "id": 410654,
                            "avg_process_sec": 1.24177
                        },
                        {
                            "date_oldest_job_queued":
                                "2012-09-28T20:29:32.640940+00:00",
                            "date_recently_completed":
                                "2012-09-28T20:30:01.549837+00:00",
                            "processors_count": 1,
                            "avg_wait_sec": 14.8803,
                            "waiting_job_count": 1,
                            "date_created": "2012-09-28T20:30:01.734137+00:00",
                            "id": 410653,
                            "avg_process_sec": 1.19637
                        }
                    ],
                    "total": 12,
                    "socorro_revision":
                        "017d7b3f7042ce76bc80949ae55b41d1e915ab62"
                }
            """)

        rget.side_effect = mocked_get

        response = models.Status().get('3')
        ok_(response['hits'])
        
    @mock.patch('requests.get')
    def test_daily_builds(self, rget):
        model = models.DailyBuilds
        api = model()

        def mocked_get(**options):
            assert 'product' in options['url']
            return Response("""
                [
                  {
                    "product": "SeaMonkey",
                    "repository": "dev",
                    "buildid": 20120625000007,
                    "beta_number": null,
                    "platform": "Mac OS X",
                    "version": "5.0a1",
                    "date": "2012-06-25",
                    "build_type": "Nightly"
                  },
                  {
                    "product": "SeaMonkey",
                    "repository": "dev",
                    "buildid": 20120625000007,
                    "beta_number": null,
                    "platform": "Windows",
                    "version": "5.0a1",
                    "date": "2012-06-25",
                    "build_type": "Nightly"
                  }
                ]
            """)

        rget.side_effect = mocked_get
        r = api.get('SeaMonkey')
        eq_(r[0]['product'], 'SeaMonkey')
        ok_(r[0]['date'])
        ok_(r[0]['version'])

    @mock.patch('requests.get')
    def test_raw_crash(self, rget):
        model = models.RawCrash
        api = model()

        def mocked_get(**options):
            assert 'crash/meta' in options['url']
            return Response("""
                {
                  "InstallTime": "1339289895",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "socorro-123@restmail.net",
                  "Vendor": "Mozilla"
                  }
            """)

        rget.side_effect = mocked_get
        r = api.get('some-crash-id')
        eq_(r['Vendor'], 'Mozilla')


class TestModelsWithFileCaching(TestCase):

    def setUp(self):
        super(TestModelsWithFileCaching, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        # Using CACHE_MIDDLEWARE_FILES is mainly for debugging but good to test
        self._cache_middleware = settings.CACHE_MIDDLEWARE
        self._cache_middleware_files = settings.CACHE_MIDDLEWARE_FILES
        settings.CACHE_MIDDLEWARE = True
        settings.CACHE_MIDDLEWARE_FILES = self.tempdir
        cache.clear()

    def tearDown(self):
        super(TestModelsWithFileCaching, self).tearDown()
        settings.CACHE_MIDDLEWARE = self._cache_middleware
        settings.CACHE_MIDDLEWARE_FILES = self._cache_middleware_files
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    @mock.patch('requests.get')
    def test_bugzilla_api_to_file(self, rget):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(**options):
            assert options['url'].startswith(models.BugzillaAPI.base_url)
            return Response('{"bugs": [{"product": "mozilla.org"}]}')

        rget.side_effect = mocked_get
        info = api.get('747237', 'product')
        eq_(info['bugs'], [{u'product': u'mozilla.org'}])

        # prove that it's cached by default
        def new_mocked_get(**options):
            return Response('{"bugs": [{"product": "DIFFERENT"}]}')

        rget.side_effect = new_mocked_get
        info = api.get('747237', 'product')
        eq_(info['bugs'], [{u'product': u'mozilla.org'}])

        info = api.get('747238', 'product')
        eq_(info['bugs'], [{u'product': u'DIFFERENT'}])

    def _get_cached_file(self, in_):
        files = []
        for f in os.listdir(in_):
            path = os.path.join(in_, f)
            if os.path.isdir(path):
                files.extend(self._get_cached_file(path))
            else:
                files.append(path)
        return files

    @mock.patch('crashstats.crashstats.models.time.time')
    @mock.patch('requests.get')
    def test_get_current_version_cache_invalidation(self, rget, mocked_time):
        def mocked_get(**options):
            assert 'current/versions/' in options['url']
            return Response("""
                {"currentversions": [{
                  "product": "Camino",
                  "throttle": "100.00",
                  "end_date": "2012-05-10 00:00:00",
                  "start_date": "2012-03-08 00:00:00",
                  "featured": true,
                  "version": "2.1.3pre",
                  "release": "Beta",
                  "id": 922}]
                  }
              """)
        rget.side_effect = mocked_get

        assert not self._get_cached_file(self.tempdir)

        # the first time, we rely on the mocket request.get
        model = models.CurrentVersions
        api = model()
        info = api.get()
        eq_(info[0]['product'], 'Camino')

        json_file = self._get_cached_file(self.tempdir)[0]
        assert 'currentversions' in json.loads(open(json_file).read())

        # if we now loose the memcache/locmem
        from django.core.cache import cache
        cache.clear()

        info = api.get()
        eq_(info[0]['product'], 'Camino')

        now = time.time()
        extra = models.CurrentVersions.cache_seconds

        def my_time():
            return now + extra

        # now we're going to mess with the modification time so that
        # the cache file gets wiped
        rget.side_effect = mocked_get

        mocked_time.side_effect = my_time
        info = api.get()
        eq_(info[0]['product'], 'Camino')
