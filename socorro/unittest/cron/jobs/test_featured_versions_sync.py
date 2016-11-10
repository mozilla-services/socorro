import datetime
import json

import mock
from nose.tools import eq_

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


class IntegrationTestFeaturedVersionsSync(IntegrationTestBase):

    def setUp(self):
        super(IntegrationTestFeaturedVersionsSync, self).setUp()
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
            )
            ,(
                2,
                'Firefox',
                '24.5',
                '24.5.0',
                '24.5.0',
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
        super(IntegrationTestFeaturedVersionsSync, self).tearDown()

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

    def _setup_config_manager(self, api_endpoint_url='https://whatever.urg'):
        return get_config_manager_for_crontabber(
            jobs=(
                'socorro.cron.jobs.featured_versions_sync'
                '.FeaturedVersionsSyncCronApp|1d'
            ),
            overrides={
                'crontabber.class-FeaturedVersionsSyncCronApp'
                '.api_endpoint_url': api_endpoint_url,
            }
        )

    @mock.patch('requests.get')
    def test_basic_run_job(self, rget):
        config_manager = self._setup_config_manager()

        def mocked_get(url):
            return Response({
                'hits': [
                    {
                        'product': 'Firefox',
                        'is_featured': True,
                        'version': '24.5.0'
                    },
                ],
                'total': 1
            })

        rget.side_effect = mocked_get

        rows = execute_query_fetchall(
            self.conn,
            'select product_name, version_string, featured_version '
            'from product_versions'
        )
        eq_(
            sorted(rows),
            [('Firefox', '15.0a1', True), ('Firefox', '24.5.0', False)]
        )
        # and the view `product_info`...
        rows = execute_query_fetchall(
            self.conn,
            'select product_name, version_string, is_featured '
            'from product_info'
        )
        eq_(
            sorted(rows),
            [('Firefox', '15.0a1', True), ('Firefox', '24.5.0', False)]
        )
        # This is necessary so we get a new cursor when we do other
        # selects after the crontabber app has run.
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['featured-versions-sync']
            assert not information['featured-versions-sync']['last_error']
            assert information['featured-versions-sync']['last_success']

            config.logger.info.assert_called_with(
                'Set featured versions for Firefox %r' % (
                    [u'24.5.0'],
                )
            )

        rows = execute_query_fetchall(
            self.conn,
            'select product_name, version_string, featured_version '
            'from product_versions'
        )
        eq_(
            sorted(rows),
            [('Firefox', '15.0a1', False), ('Firefox', '24.5.0', True)]
        )
        # and the view `product_info`...
        rows = execute_query_fetchall(
            self.conn,
            'select product_name, version_string, is_featured '
            'from product_info'
        )
        eq_(
            sorted(rows),
            [('Firefox', '15.0a1', False), ('Firefox', '24.5.0', True)]
        )
