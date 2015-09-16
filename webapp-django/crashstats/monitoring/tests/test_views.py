import datetime
import json

from nose.tools import eq_, ok_
import mock

from django.core.urlresolvers import reverse
from django.conf import settings

from crashstats.crashstats.tests.test_views import BaseTestViews, Response


class TestViews(BaseTestViews):

    def test_index(self):
        url = reverse('monitoring:index')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_(reverse('monitoring:crash_analysis_health') in response.content)
        ok_(reverse('monitoring:crontabber_status') in response.content)


class TestCrashAnalysisHealthViews(BaseTestViews):

    @mock.patch('requests.get')
    def test_all_good(self, rget):

        def mocked_get(url, **params):
            return Response("""
                <a href="file.txt">file.txt</a> 2015-08-19 123
                <a href="file2.txt">file2.txt</a> 2015-08-19  1
            """)

        rget.side_effect = mocked_get
        assert settings.CRASH_ANALYSIS_MONITOR_DAYS_BACK == 2
        url = reverse('monitoring:crash_analysis_health')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'ALLGOOD')
        ok_(not data.get('errors'))
        ok_(not data.get('warnings'))

    @mock.patch('requests.get')
    def test_all_good_with_warning(self, rget):

        today = datetime.datetime.utcnow().date()

        def mocked_get(url, **params):
            if today.strftime('%Y%m%d') in url:
                return Response('Not found', 404)
            return Response("""
                <a href="file.txt">file.txt</a> 2015-08-19 123
                <a href="file2.txt">file2.txt</a> 2015-08-19  1
            """)

        rget.side_effect = mocked_get
        url = reverse('monitoring:crash_analysis_health')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'ALLGOOD')
        ok_(not data.get('errors'))
        eq_(len(data['warnings']), 1)
        ok_('not yet been created' in data['warnings'][0])

    @mock.patch('requests.get')
    def test_broken_no_sub_directory(self, rget):

        def mocked_get(url, **params):
            return Response('Not found', 404)

        rget.side_effect = mocked_get
        url = reverse('monitoring:crash_analysis_health')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'Broken')
        ok_(data['errors'])
        ok_('No sub-directory created' in data['errors'][0])
        eq_(len(data['warnings']), 1)
        ok_('not yet been created' in data['warnings'][0])

    @mock.patch('requests.get')
    def test_broken_empty_files(self, rget):

        def mocked_get(url, **params):
            return Response("""
                <a href="file.txt">file.txt</a>   2015-08-19    0
                <a href="file2.txt">file2.txt</a> 2015-08-19    0
            """)

        rget.side_effect = mocked_get
        url = reverse('monitoring:crash_analysis_health')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'ALLGOOD')
        eq_(len(data['warnings']), 2)
        ok_('contains a 0-bytes sized file' in data['warnings'][0])

    @mock.patch('requests.get')
    def test_broken_not_files(self, rget):

        def mocked_get(url, **params):
            return Response("""
                Nothing here
                Don't be misled by a regular link like this:
                <a href="file.html">Page whatever</a>
            """)

        rget.side_effect = mocked_get
        url = reverse('monitoring:crash_analysis_health')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'Broken')
        eq_(len(data['errors']), 2)
        ok_('contains no valid file links' in data['errors'][0])


class TestCrontabberStatusViews(BaseTestViews):

    @mock.patch('requests.get')
    def test_crontabber_status_ok(self, rget):

        def mocked_get(url, **options):
            assert '/crontabber_state/' in url
            return Response({
                'state': {
                    'job1': {
                        'error_count': 0,
                        'depends_on': []
                    }
                }
            })

        rget.side_effect = mocked_get

        url = reverse('monitoring:crontabber_status')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {'status': 'ALLGOOD'})

    @mock.patch('requests.get')
    def test_crontabber_status_trouble(self, rget):

        def mocked_get(url, **options):
            assert '/crontabber_state/' in url
            return Response({
                'state': {
                    'job1': {
                        'error_count': 1,
                        'depends_on': [],
                    },
                    'job2': {
                        'error_count': 0,
                        'depends_on': ['job1'],
                    },
                    'job3': {
                        'error_count': 0,
                        'depends_on': ['job2'],
                    },
                    'job1b': {
                        'error_count': 0,
                        'depends_on': [],
                    },
                }
            })

        rget.side_effect = mocked_get

        url = reverse('monitoring:crontabber_status')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'Broken')
        eq_(data['broken'], ['job1'])
        eq_(data['blocked'], ['job2', 'job3'])
