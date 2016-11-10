import datetime
import json

import mock
from nose.tools import eq_, ok_

from crontabber.app import CronTabber
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


from socorro.lib.datetimeutil import utc_now
from socorro.unittest.cron.jobs.base import IntegrationTestBase
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
)


class Response(object):
    def __init__(self, content, status_code=200):
        if not isinstance(content, basestring):
            content = json.dumps(content)
        self.content = content.strip()
        self.status_code = status_code

    def json(self):
        return json.loads(self.content)


class IntegrationTestFeaturedVersionsAutomatic(IntegrationTestBase):

    def setUp(self):
        super(IntegrationTestFeaturedVersionsAutomatic, self).setUp()
        self.__truncate()

        now = utc_now()
        build_date = now - datetime.timedelta(days=30)
        sunset_date = now + datetime.timedelta(days=30)

        execute_no_results(
            self.conn,
            """
            INSERT INTO products
            (product_name, sort, release_name)
            VALUES
            ('Firefox', 1, 'firefox'),
            ('Fennec', 1, 'mobile')
            """
        )
        execute_no_results(
            self.conn,
            """
            INSERT INTO product_versions
            (product_version_id, product_name, major_version, release_version,
            version_string, version_sort, build_date, sunset_date,
            featured_version, build_type)
            VALUES
            (
                1,
                'Firefox',
                '15.0',
                '15.0',
                '15.0a1',
                '000000150a1',
                %(build_date)s,
                %(sunset_date)s,
                true,
                'release'
            ),
            (
                2,
                'Firefox',
                '24.5',
                '24.5.0',
                '24.5.0',
                '024005000x000',
                %(build_date)s,
                %(sunset_date)s,
                true,
                'nightly'
            ),
            (
                3,
                'Firefox',
                '49.0.1',
                '49.0.1',
                '49.0.1',
                '000000150a1',
                %(build_date)s,
                %(sunset_date)s,
                false,
                'release'
            ),
            (
                4,
                'Firefox',
                '50.0b',
                '50.0b',
                '50.0b',
                '024005000x000',
                %(build_date)s,
                %(sunset_date)s,
                false,
                'beta'
            ),
            (
                5,
                'Firefox',
                '51.0a2',
                '51.0a2',
                '51.0a2',
                '000000150a1',
                %(build_date)s,
                %(sunset_date)s,
                false,
                'aurora'
            ),
            (
                6,
                'Firefox',
                '52.0a1',
                '52.0a1',
                '52.0a1',
                '024005000x000',
                %(build_date)s,
                %(sunset_date)s,
                false,
                'nightly'
            )
            """,
            {
                'build_date': build_date,
                'sunset_date': sunset_date
            }
        )
        execute_no_results(
            self.conn,
            """
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('nightly', 1),
            ('aurora', 2),
            ('beta', 3),
            ('release', 4)
            """
        )
        execute_no_results(
            self.conn,
            """
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            ('Firefox', 'nightly', 1),
            ('Firefox', 'aurora', 1),
            ('Firefox', 'beta', 1),
            ('Firefox', 'release', 1),
            ('Fennec', 'release', 1),
            ('Fennec', 'beta', 1)
            """
        )

    def tearDown(self):
        self.__truncate()
        super(IntegrationTestFeaturedVersionsAutomatic, self).tearDown()

    def __truncate(self):
        """Named like this because the parent class has a _truncate()
        which won't be executed by super(IntegrationTestFeaturedVersionsSync)
        in its setUp()."""
        self.conn.cursor().execute("""
        TRUNCATE
            products,
            product_versions,
            release_channels,
            product_release_channels
        CASCADE
        """)
        self.conn.commit()

    def _setup_config_manager(self):
        return get_config_manager_for_crontabber(
            jobs=(
                'socorro.cron.jobs.featured_versions_automatic'
                '.FeaturedVersionsAutomaticCronApp|1d'
            ),
            overrides={
                'crontabber.class-FeaturedVersionsAutomaticCronApp'
                '.api_endpoint_url': (
                    'https://example.com/{product}_versions.json'
                ),
            }
        )

    @mock.patch('requests.get')
    def test_basic_run_job(self, rget):
        config_manager = self._setup_config_manager()

        def mocked_get(url):
            if 'firefox_versions.json' in url:
                return Response({
                    'FIREFOX_NIGHTLY': '52.0a1',
                    'FIREFOX_AURORA': '51.0a2',
                    'FIREFOX_ESR': '45.4.0esr',
                    'FIREFOX_ESR_NEXT': '',
                    'LATEST_FIREFOX_DEVEL_VERSION': '50.0b7',
                    'LATEST_FIREFOX_OLDER_VERSION': '3.6.28',
                    'LATEST_FIREFOX_RELEASED_DEVEL_VERSION': '50.0b7',
                    'LATEST_FIREFOX_VERSION': '49.0.1'
                })
            elif 'mobile_versions.json' in url:
                return Response({
                    'nightly_version': '52.0a1',
                    'alpha_version': '51.0a2',
                    'beta_version': '50.0b6',
                    'version': '49.0',
                    'ios_beta_version': '6.0',
                    'ios_version': '5.0'
                })
            elif 'thunderbird_versions.json' in url:
                return Response({
                    'LATEST_THUNDERBIRD_VERSION': '45.4.0',
                    'LATEST_THUNDERBIRD_DEVEL_VERSION': '50.0b1',
                    'LATEST_THUNDERBIRD_ALPHA_VERSION': '51.0a2'
                })
            else:
                raise NotImplementedError(url)

        rget.side_effect = mocked_get

        # Check what's set up in the fixture
        rows = execute_query_fetchall(
            self.conn,
            'select product_name, version_string, featured_version '
            'from product_versions order by version_string'
        )
        assert sorted(rows) == [
            ('Firefox', '15.0a1', True),
            ('Firefox', '24.5.0', True),
            ('Firefox', '49.0.1', False),
            ('Firefox', '50.0b', False),
            ('Firefox', '51.0a2', False),
            ('Firefox', '52.0a1', False),
        ]

        # This is necessary so we get a new cursor when we do other
        # selects after the crontabber app has run.
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['featured-versions-automatic']
            assert not information['featured-versions-automatic']['last_error']
            assert information['featured-versions-automatic']['last_success']

            config.logger.info.assert_called_with(
                'Set featured versions for Thunderbird to: '
                '45.4.0, 50.0b1, 51.0a2'
            )

        rows = execute_query_fetchall(
            self.conn,
            'select product_name, version_string, featured_version '
            'from product_versions'
        )
        eq_(
            sorted(rows),
            [
                ('Firefox', '15.0a1', False),
                ('Firefox', '24.5.0', False),
                ('Firefox', '49.0.1', True),
                ('Firefox', '50.0b', True),
                ('Firefox', '51.0a2', True),
                ('Firefox', '52.0a1', True),
            ]
        )

    @mock.patch('requests.get')
    def test_download_error(self, rget):
        config_manager = self._setup_config_manager()

        def mocked_get(url):
            return Response('not here', status_code=404)

        rget.side_effect = mocked_get

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['featured-versions-automatic']
            assert information['featured-versions-automatic']['last_error']
            error = information['featured-versions-automatic']['last_error']
            ok_('DownloadError' in error['type'])
            ok_('404' in error['value'])
