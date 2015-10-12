# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import contextlib

import mock
from nose.tools import eq_, ok_

from crontabber.app import CronTabber
from socorro.unittest.cron.jobs.base import IntegrationTestBase
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


class TestFetchADIFromHive(IntegrationTestBase):

    def setUp(self):
        super(TestFetchADIFromHive, self).setUp()
        # Add something to product_productid_map
        cursor = self.conn.cursor()
        cursor.execute("""
            TRUNCATE
                raw_adi, raw_adi_logs, product_productid_map, products
            CASCADE
        """)
        cursor.execute("""
            INSERT into products (
                product_name,
                release_name
            ) VALUES (
                'WinterWolf', 'release'
            ), (
                'NothingMuch', 'release'
            ), (
                'FennecAndroid', 'release'
            )
        """)
        cursor.execute("""
            INSERT into product_productid_map (
                product_name,
                productid
            ) VALUES (
                'NothingMuch', '{webapprt@mozilla.org}'
            ), (
                'WinterWolf', 'a-guid'
            )
        """)
        self.conn.commit()

    def tearDown(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            TRUNCATE
                raw_adi, raw_adi_logs, product_productid_map, products
            CASCADE
        """)
        super(TestFetchADIFromHive, self).tearDown()

    def _setup_config_manager(self, overrides=None):
        return get_config_manager_for_crontabber(
            jobs=(
                'socorro.cron.jobs.fetch_adi_from_hive'
                '.FetchADIFromHiveCronApp|1d'
            ),
            overrides=overrides,
        )

    @mock.patch('socorro.cron.jobs.fetch_adi_from_hive.pyhs2')
    def test_mocked_fetch(self, fake_hive):
        config_manager = self._setup_config_manager()

        yesterday = (
            datetime.datetime.utcnow() - datetime.timedelta(days=1)
        ).date()

        def return_test_data(fake):
            yield [
                yesterday,
                'WinterWolf',
                'Ginko',
                '2.3.1',
                '10.0.4',
                'nightly-ww3v20',
                'nightly',
                'a-guid',
                1
            ]
            yield [
                yesterday,
                'NothingMuch',
                'Ginko',
                '3.2.1',
                '10.0.4',
                'release-ww3v20',
                'release-cck-blah',
                'webapprt@mozilla.org',
                1
            ]
            yield [
                '2019-01-01',
                'NothingMuch',
                u'Ginko☢\0',
                '2.3.2',
                '10.0.5a',
                'release',
                'release-cck-\\',
                '%7Ba-guid%7D',
                2
            ]
            yield [
                '2019-01-01',
                'Missing',
                'Ginko',
                '2.3.2',
                '',
                None,
                'release',
                '%7Ba-guid%7D',
                2
            ]
            yield [
                yesterday,
                'FennecAndroid',   # product name
                'Ginko',           # platform?
                '3.1415',          # platform version
                '38.0',            # product version
                '20150427090529',  # build
                'release',         # update channel
                'a-guid',          # product guid
                666                # count
            ]

        fake_hive.connect.return_value \
            .cursor.return_value.__iter__ = return_test_data

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['fetch-adi-from-hive']
            assert not information['fetch-adi-from-hive']['last_error']

        fake_hive.connect.assert_called_with(
            database='default',
            authMechanism='PLAIN',
            host='localhost',
            user='socorro',
            password='ignored',
            port=10000,
            timeout=1800000,
        )

        pgcursor = self.conn.cursor()
        columns = (
            'report_date',
            'product_name',
            'product_os_platform',
            'product_os_version',
            'product_version',
            'build',
            'build_channel',
            'product_guid',
            'count'
        )
        pgcursor.execute(
            "select %s from raw_adi_logs" % ','.join(columns)
        )
        adi_logs = [dict(zip(columns, row)) for row in pgcursor.fetchall()]
        eq_(adi_logs[0], {
            'report_date': yesterday,
            'product_name': 'WinterWolf',
            'product_os_platform': 'Ginko',
            'product_os_version': '2.3.1',
            'product_version': '10.0.4',
            'build': 'nightly-ww3v20',
            'build_channel': 'nightly',
            'product_guid': 'a-guid',
            'count': 1
        })
        eq_(adi_logs[1], {
            'report_date': yesterday,
            'product_name': 'NothingMuch',
            'product_os_platform': 'Ginko',
            'product_os_version': '3.2.1',
            'product_version': '10.0.4',
            'build': 'release-ww3v20',
            'build_channel': 'release-cck-blah',
            'product_guid': 'webapprt@mozilla.org',
            'count': 1
        })
        eq_(adi_logs[2], {
            'report_date': datetime.date(2019, 1, 1),
            'product_name': 'NothingMuch',
            'product_os_platform': 'Ginko\xe2\x98\xa2',
            'product_os_version': '2.3.2',
            'product_version': '10.0.5a',
            'build': 'release',
            'build_channel': 'release-cck-\\',
            'product_guid': '{a-guid}',
            'count': 2
        })
        eq_(adi_logs[3], {
            'report_date': yesterday,
            'product_name': 'FennecAndroid',
            'product_os_platform': 'Ginko',
            'product_os_version': '3.1415',
            'product_version': '38.0',
            'build': '20150427090529',
            'build_channel': 'release',
            'product_guid': 'a-guid',
            'count': 666
        })

        columns = (
            'adi_count',
            'date',
            'product_name',
            'product_os_platform',
            'product_os_version',
            'product_version',
            'build',
            'product_guid',
            'update_channel',
        )
        pgcursor.execute(
            """ select %s from raw_adi
                order by update_channel desc""" % ','.join(columns)
        )
        adi = [dict(zip(columns, row)) for row in pgcursor.fetchall()]
        eq_(adi[0], {
            'update_channel': 'release',
            'product_guid': '{webapprt@mozilla.org}',
            'product_version': '10.0.4',
            'adi_count': 1,
            'product_os_platform': 'Ginko',
            'build': 'release-ww3v20',
            'date': yesterday,
            'product_os_version': '3.2.1',
            'product_name': 'NothingMuch'
        })
        eq_(adi[1], {
            'update_channel': 'nightly',
            'product_guid': 'a-guid',
            'product_version': '10.0.4',
            'adi_count': 1,
            'product_os_platform': 'Ginko',
            'build': 'nightly-ww3v20',
            'date': yesterday,
            'product_os_version': '2.3.1',
            'product_name': 'WinterWolf'
        })
        eq_(adi[2], {
            'update_channel': 'beta',
            'product_guid': 'a-guid',
            'product_version': '38.0',
            'adi_count': 666,
            'product_os_platform': 'Ginko',
            'build': '20150427090529',
            'date': yesterday,
            'product_os_version': '3.1415',
            'product_name': 'FennecAndroid'
        })

    @mock.patch('socorro.cron.jobs.fetch_adi_from_hive.pyhs2')
    def test_mocked_fetch_with_secondary_destination(self, fake_hive):

        class MockedPGConnectionContext:
            connection = mock.MagicMock()

            def __init__(self, config):
                self.config = config

            @contextlib.contextmanager
            def __call__(self):
                yield self.connection

        config_manager = self._setup_config_manager(
            overrides={
                'crontabber.class-FetchADIFromHiveCronApp.'
                'secondary_destination.'
                'database_class': MockedPGConnectionContext,
            }
        )

        yesterday = (
            datetime.datetime.utcnow() - datetime.timedelta(days=1)
        ).date()

        def return_test_data(fake):
            yield [
                yesterday,
                'WinterWolf',
                'Ginko',
                '2.3.1',
                '10.0.4',
                'nightly-ww3v20',
                'nightly',
                'a-guid',
                1
            ]

        fake_hive.connect.return_value \
            .cursor.return_value.__iter__ = return_test_data

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['fetch-adi-from-hive']
            assert not information['fetch-adi-from-hive']['last_error']

        fake_hive.connect.assert_called_with(
            database='default',
            authMechanism='PLAIN',
            host='localhost',
            user='socorro',
            password='ignored',
            port=10000,
            timeout=1800000,
        )

        # Critical test here.
        # We make sure the secondary database class gets used
        # for a `cursor.copy_from()` call.
        ok_(MockedPGConnectionContext.connection.cursor().copy_from.called)
