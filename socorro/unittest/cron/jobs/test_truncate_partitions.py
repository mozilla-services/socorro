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
class TestTruncatePartitions(IntegrationTestBase):

    def _setup_config_manager(self):
        super(TestTruncatePartitions, self)._setup_config_manager
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.truncate_partitions.'
            'TruncatePartitionsCronApp|1m',
        )

    def setUp(self):
        super(TestTruncatePartitions, self).setUp()

        cur = self.conn.cursor()

        # Ensure the test database and partition entry exist.
        statement = """
        CREATE TABLE raw_crashes_20120102(foo TEXT);
        INSERT INTO report_partition_info (table_name, partition_column,
        timetype) VALUES ('raw_crashes', 'date_processed', 'TIMESTAMPTZ');
        INSERT INTO raw_crashes_20120102 VALUES ('things'), ('bother');
        """
        cur.execute(statement)

        self.conn.commit()

    def tearDown(self):
        cur = self.conn.cursor()

        # Ensure that the test partition entry and table no longer exist.
        statement = """
        DELETE FROM report_partition_info WHERE table_name = 'raw_crashes';
        DROP TABLE IF EXISTS raw_crashes_20120102;
        """
        cur.execute(statement)

        self.conn.commit()

        super(TestTruncatePartitions, self).tearDown()

    def test_run_drop_old_partitions(self):
        cur = self.conn.cursor()

        # Ensure test table is present.
        statement = """
        SELECT COUNT(*) FROM raw_crashes_20120102;
        """
        cur.execute(statement)
        result = cur.fetchone()
        eq_(result[0], 2L)
        # need to get out of this transaction to
        # allow crontabber to acquire a lock
        self.conn.commit()

        # Run the crontabber job to remove the test table.
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

        # Basic assertion test of stored procedure.
        information = self._load_structure()
        print information['truncate-partitions']['last_error']
        assert information['truncate-partitions']
        assert not information['truncate-partitions']['last_error']
        assert information['truncate-partitions']['last_success']

        # Ensure test table was removed.
        statement = """
        SELECT COUNT(*) FROM raw_crashes_20120102;
        """
        cur.execute(statement)
        result = cur.fetchone()
        eq_(result[0], 0)
