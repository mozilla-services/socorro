# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose.tools import eq_
from crontabber.app import CronTabber
from socorro.unittest.cron.jobs.base import IntegrationTestBase
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


@attr(integration='postgres')
class TestDropOldPartitions(IntegrationTestBase):

    def _setup_config_manager(self):
        _super = super(TestDropOldPartitions, self)._setup_config_manager
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.drop_old_partitions.'
            'DropOldPartitionsCronApp|1m',
        )

    def setUp(self):
        super(TestDropOldPartitions, self).setUp()

        cur = self.conn.cursor()

        # Ensure the test database and partition entry exist.
        statement = """
        CREATE TABLE phrotest_20120102();
        INSERT INTO report_partition_info (table_name, partition_column,
        timetype) VALUES ('phrotest', 'date_processed', 'TIMESTAMPTZ');
        """
        cur.execute(statement)

        self.conn.commit()

    def tearDown(self):
        cur = self.conn.cursor()

        # Ensure that the test partition entry and table no longer exist.
        statement = """
        DELETE FROM report_partition_info WHERE table_name = 'phrotest';
        DROP TABLE IF EXISTS phrotest_20120102;
        """
        cur.execute(statement)

        self.conn.commit()

        super(TestDropOldPartitions, self).tearDown()

    def test_run_drop_old_partitions(self):
        cur = self.conn.cursor()

        # Ensure test table is present.
        statement = """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'phrotest_20120102';
        """
        cur.execute(statement)
        result = cur.fetchone()
        eq_(result[0], 1)

        # Run the crontabber job to remove the test table.
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

        # Basic assertion test of stored procedure.
        information = self._load_structure()
        assert information['drop-old-partitions']
        assert not information['drop-old-partitions']['last_error']
        assert information['drop-old-partitions']['last_success']

        # Ensure test table was removed.
        statement = """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'phrotest_20120102';
        """
        cur.execute(statement)
        result = cur.fetchone()
        eq_(result[0], 0)
