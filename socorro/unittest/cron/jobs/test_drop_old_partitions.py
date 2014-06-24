# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from crontabber.app import CronTabber
from crontabber.tests.base import IntegrationTestCaseBase


# The name of the test table used below.
TABLE = 'phrotest_20120102'
TABID = 'phrotest'


@attr(integration='postgres')
class TestDropOldPartitions(IntegrationTestCaseBase):

    def _setup_config_manager(self):
        _super = super(TestDropOldPartitions, self)._setup_config_manager
        return _super(
            'socorro.cron.jobs.drop_old_partitions.'
            'DropOldPartitionsCronApp|1m',
        )

    def setUp(self):
        super(TestDropOldPartitions, self).setUp()

        cur = self.conn.cursor()

        # Ensure the test database and partition entry exist.
        statement = """
        CREATE TABLE %s();
        INSERT INTO report_partition_info (table_name, partition_column,
        timetype) VALUES ('%s', 'date_processed', 'TIMESTAMPTZ');
        """ % (TABLE, TABID)
        cur.execute(statement)

        cur.close()
        self.conn.commit()

    def tearDown(self):
        cur = self.conn.cursor()

        # Ensure that the test partition entry and table no longer exist.
        statement = """
        DELETE FROM report_partition_info WHERE table_name = '%s';
        DROP TABLE IF EXISTS %s;
        """ % (TABID, TABLE)
        cur.execute(statement)

        cur.close()
        self.conn.commit()

        super(TestDropOldPartitions, self).tearDown()

    def test_run_drop_old_partitions(self):
        cur = self.conn.cursor()

        # Ensure test table is present.
        statement = """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = '%s';
        """ % (TABLE)
        cur.execute(statement)
        result = cur.fetchone()
        assert result[0] == 1

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
        WHERE table_name = '%s';
        """ % (TABLE)
        cur.execute(statement)
        result = cur.fetchone()
        assert result[0] == 0

        cur.close()
        self.conn.commit()
