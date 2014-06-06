# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from mock import patch
from nose.plugins.attrib import attr
from nose.tools import eq_

from crontabber.app import CronTabber
from crontabber.tests.base import IntegrationTestCaseBase

from socorro.cron.jobs import fetch_adi_from_hive


@attr(integration='postgres')
class TestFetchADIFromHive(IntegrationTestCaseBase):

    def setUp(self):
        super(TestFetchADIFromHive, self).setUp()
        self.conn.commit()

    def tearDown(self):
        cursor = self.conn.cursor()
        cursor.execute("TRUNCATE raw_adi_logs")
        self.conn.commit()
        super(TestFetchADIFromHive, self).tearDown()

    def _setup_config_manager(self):
        _super = super(TestFetchADIFromHive, self)._setup_config_manager
        return _super(
            'socorro.cron.jobs.fetch_adi_from_hive.FetchADIFromHiveCronApp|1d'
        )

    def test_mocked_fetch(self):
        config_manager = self._setup_config_manager()

        def return_test_data(fake):
            test_data = [['2014-01-01', 'WinterWolf', 'Ginko', '2.3.1', '10.0.4', 'nightly-ww3v20', 'nightly', 'a-guid', '1']]
            for item in test_data:
                yield item

        with patch('socorro.cron.jobs.fetch_adi_from_hive.pyhs2') as fake_hive:
            fake_hive.connect.return_value \
                .cursor.return_value.__iter__ = return_test_data

            with config_manager.context() as config:
                tab = CronTabber(config)
                tab.run_all()

                information = self._load_structure()
                assert information['fetch-adi-from-hive']

                if information['fetch-adi-from-hive']['last_error']:
                    raise AssertionError(information['fetch-adi-from-hive']['last_error'])

        fake_hive.connect.assert_called_with(database='default', authMechanism='PLAIN', host='localhost', user='socorro', password='ignored', port=10000)
        fake_hive.connect.cursor.assert_called()
        fake_hive.connect.cursor.execute.assert_called()
        fake_hive.connect.cursor.__iter__.assert_called()

        pgcursor = self.conn.cursor()
        columns = 'report_date',\
            'product_name',\
            'product_os_platform',\
            'product_os_version',\
            'product_version',\
            'build',\
            'build_channel',\
            'product_guid',\
            'count'
        pgcursor.execute(""" select %s from raw_adi_logs """
            % ','.join(columns))

        adi = [dict(zip(columns, row)) for row in pgcursor.fetchall()]

        eq_(adi, [{
                 'report_date': datetime.date(2014, 1, 1),
                 'product_name': 'WinterWolf',
                 'product_os_platform': 'Ginko',
                 'product_os_version': '2.3.1',
                 'product_version': '10.0.4',
                 'build': 'nightly-ww3v20',
                 'build_channel': 'nightly',
                 'product_guid': 'a-guid',
                 'count': 1
        }])
