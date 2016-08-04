import datetime
import json

from nose.tools import eq_, ok_, assert_raises
import mock

from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import timezone

from crashstats.crashstats.tests.test_views import BaseTestViews, Response
from crashstats.crashstats.models import CrontabberState
from crashstats.supersearch.models import SuperSearch
from crashstats.monitoring.views import assert_supersearch_no_errors


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

    def test_crontabber_status_ok(self):

        def mocked_get(**options):
            recently = timezone.now()
            return {
                'state': {
                    'job1': {
                        'error_count': 0,
                        'depends_on': [],
                        'last_run': recently,
                    }
                }
            }

        CrontabberState.implementation().get.side_effect = mocked_get

        url = reverse('monitoring:crontabber_status')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {'status': 'ALLGOOD'})

    def test_crontabber_status_trouble(self):

        def mocked_get(**options):
            recently = timezone.now()
            return {
                'state': {
                    'job1': {
                        'error_count': 1,
                        'depends_on': [],
                        'last_run': recently,
                    },
                    'job2': {
                        'error_count': 0,
                        'depends_on': ['job1'],
                        'last_run': recently,
                    },
                    'job3': {
                        'error_count': 0,
                        'depends_on': ['job2'],
                        'last_run': recently,
                    },
                    'job1b': {
                        'error_count': 0,
                        'depends_on': [],
                        'last_run': recently,
                    },
                }
            }

        CrontabberState.implementation().get.side_effect = mocked_get

        url = reverse('monitoring:crontabber_status')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'Broken')
        eq_(data['broken'], ['job1'])
        eq_(data['blocked'], ['job2', 'job3'])

    def test_crontabber_status_not_run_for_a_while(self):

        some_time_ago = (
            timezone.now() - datetime.timedelta(
                minutes=settings.CRONTABBER_STALE_MINUTES
            )
        )

        def mocked_get(**options):
            return {
                'state': {
                    'job1': {
                        'error_count': 0,
                        'depends_on': [],
                        'last_run': some_time_ago,
                    },
                    'job2': {
                        'error_count': 0,
                        'depends_on': ['job1'],
                        'last_run': some_time_ago,
                    },
                }
            }

        CrontabberState.implementation().get.side_effect = mocked_get

        url = reverse('monitoring:crontabber_status')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'Stale')
        eq_(data['last_run'], some_time_ago.isoformat())

    def test_crontabber_status_never_run(self):

        def mocked_get(**options):
            return {
                'state': {}
            }

        CrontabberState.implementation().get.side_effect = mocked_get

        url = reverse('monitoring:crontabber_status')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'Stale')


class TestHealthcheckViews(BaseTestViews):

    def test_healthcheck_elb(self):
        url = reverse('monitoring:healthcheck')
        response = self.client.get(url, {'elb': 'true'})
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['ok'], True)

        # This time, ignoring the results, make sure that running
        # this does not cause an DB queries.
        self.assertNumQueries(
            0,
            self.client.get,
            url,
            {'elb': 'true'}
        )

    @mock.patch('requests.get')
    @mock.patch('crashstats.monitoring.views.elasticsearch')
    def test_healthcheck(self, mocked_elasticsearch, rget):
        searches = []

        def mocked_supersearch_get(**params):
            searches.append(params)
            eq_(params['product'], [settings.DEFAULT_PRODUCT])
            eq_(params['_results_number'], 1)
            eq_(params['_columns'], ['uuid'])
            return {
                'hits': [
                    {'uuid': '12345'},
                ],
                'facets': [],
                'total': 30002,
                'errors': [],
            }

        SuperSearch.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        def mocked_requests_get(url, **params):
            return Response(True)

        rget.side_effect = mocked_requests_get

        url = reverse('monitoring:healthcheck')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['ok'], True)

        assert len(searches) == 1

    def test_assert_supersearch_errors(self):
        searches = []

        def mocked_supersearch_get(**params):
            searches.append(params)
            eq_(params['product'], [settings.DEFAULT_PRODUCT])
            eq_(params['_results_number'], 1)
            eq_(params['_columns'], ['uuid'])
            return {
                'hits': [
                    {'uuid': '12345'},
                ],
                'facets': [],
                'total': 320,
                'errors': ['bad'],
            }

        SuperSearch.implementation().get.side_effect = (
            mocked_supersearch_get
        )
        assert_raises(
            AssertionError,
            assert_supersearch_no_errors
        )
        assert len(searches) == 1
