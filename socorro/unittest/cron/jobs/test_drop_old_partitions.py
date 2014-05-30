# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose import with_setup
from crontabber.app import CronTabber
from crontabber.tests.base import IntegrationTestCaseBase


@attr(integration='postgres')
class TestDropOldPartitions(IntegrationTestCaseBase):

    def _setup_config_manager(self):
        _super = super(TestDropOldPartitions, self)._setup_config_manager
        return _super(
            'socorro.cron.jobs.drop_old_partitions.'
            'DropOldPartitionsCronApp|7d',
        )

    def setUp(self):
        super(TestDropOldPartitions, self).setUp()

        # Ensure the test database and partition entry exist.
        self.conn.cursor().execute("""
        create table phrotest_20120102();
        insert into report_partition_info (table_name, partition_column,
        timetype) values ('phrotest', 'date_processed', 'TIMESTAMPTZ');
        """)
        self.conn.commit()

    def tearDown(self):
        # Ensure that the test partition entry no longer exists.
        self.conn.cursor().execute("""
        delete from report_partition_info where table_name = 'phrotest';
        """)
        self.conn.commit()

        super(TestDropOldPartitions, self).tearDown()

    def test_run_drop_old_partitions(self):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['drop-old-partitions']
            assert not information['drop-old-partitions']['last_error']
            assert information['drop-old-partitions']['last_success']
