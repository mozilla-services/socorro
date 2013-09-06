# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .unittestbase import PostgreSQLTestCase
from nose.plugins.attrib import attr
import datetime

from socorro.external.postgresql.backfill import Backfill
from socorro.external.postgresql import fakedata
from socorro.external import MissingOrBadArgumentError
from socorro.lib import datetimeutil


#==============================================================================
@attr(integration='postgres')
class TestBackfill(PostgreSQLTestCase):
    """Tests the calling of all backfill functions"""

    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate tables with fake data """
        super(TestBackfill, self).setUp()

        cursor = self.connection.cursor()

        self.tables = []

        for table in fakedata.tables:
            table = table(days=1)

            table_name = table.table
            table_columns = table.columns
            values = str(tuple(["%(" + i + ")s" for i in table_columns]))
            columns = str(tuple(table_columns))
            self.tables.append(table_name)

            # TODO: backfill_reports_clean() sometimes tries to insert a
            # os_version_id that already exists
            if table_name is not "os_versions":
                for rows in table.generate_rows():
                    data = dict(zip(table_columns, rows))
                    query = "INSERT INTO %(table)s " % {'table': table_name}
                    query = query + columns.replace("'", "").replace(",)", ")")
                    query = query + " VALUES "
                    query = query + values.replace(",)", ")").replace("'", "")

                    cursor.execute(query, data)
                    self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """

        cursor = self.connection.cursor()
        tables = str(self.tables).replace("[", "").replace("]", "")
        cursor.execute("TRUNCATE " + tables.replace("'", "") + " CASCADE;")

        self.connection.commit()
        self.connection.close()

        super(TestBackfill, self).tearDown()

    #--------------------------------------------------------------------------
    def setup_data(self):

        self.now = datetimeutil.utc_now()
        now = self.now.date()
        yesterday = now - datetime.timedelta(days=1)
        lastweek = now - datetime.timedelta(days=7)
        now_str = datetimeutil.date_to_string(now)
        yesterday_str = datetimeutil.date_to_string(yesterday)
        lastweek_str = datetimeutil.date_to_string(lastweek)

        self.test_source_data = {
            # Test backfill_adu
            'adu': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_all_dups
            'all_dups': {
                'params': {
                    "start_date": yesterday_str,
                    "end_date": now_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_build_adu
            'build_adu': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_correlations
            'correlations': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_crashes_by_user_build
            'crashes_by_user_build': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_crashes_by_user
            'crashes_by_user': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },

            # TODO: Test backfill_daily_crashes tries to insert into a table
            # that do not exists. It can be fixed by creating a temporary one.
            #'daily_crashes': {
            #    'params': {
            #        "update_day": now_str,
            #    },
            #    'res_expected': [(True,)],
            # },

            # Test backfill_exploitability
            'exploitability': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_explosiveness
            'explosiveness': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_home_page_graph_build
            'home_page_graph_build': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_home_page_graph
            'home_page_graph': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_matviews
            'matviews': {
                'params': {
                    "start_date": yesterday_str,
                    "reports_clean": 'false',
                },
                'res_expected': [(True,)],
            },
            # Test backfill_nightly_builds
            'nightly_builds': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_one_day
            'one_day': {
                'params': {
                    "update_day": now_str,
                },
                'res_expected': [('done',)],
            },
            # Test backfill_rank_compare
            'rank_compare': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_reports_clean
            'reports_clean': {
                'params': {
                    "start_date": yesterday_str,
                    "end_date": now_str,
                },
                'res_expected': [(True,)],
            },

            # TODO: Test backfill_reports_duplicates tries to insert into a
            # table that do not exists. It can be fixed by using the update
            # function inside of the backfill.
            #'reports_duplicates': {
            #    'params': {
            #        "start_date": yesterday_str,
            #        "end_date": now_str,
            #    },
            #    'res_expected': [(True,)],
            # },

            # TODO: Test backfill_signature_counts tries to insert into
            # tables and to update functions that does not exist.
            #'signature_counts': {
            #    'params': {
            #        "start_date": yesterday_str,
            #        "end_date": now_str,
            #    },
            #    'res_expected': [(True,)],
            # },

            # Test backfill_signature_summary
            'signature_summary': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_tcbs_build
            'tcbs_build': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_tcbs
            'tcbs': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test backfill_weekly_report_partitions
            'weekly_report_partitions': {
                'params': {
                    "start_date": lastweek_str,
                    "end_date": now_str,
                    "table_name": 'raw_crashes',
                },
                'res_expected': [(True,)],
            },
        }

   #--------------------------------------------------------------------------
    def test_get(self):

        backfill = Backfill(config=self.config)

        #......................................................................
        # Test raise error if kind of backfill is not passed
        params = {"backfill_type": ''}
        self.assertRaises(MissingOrBadArgumentError, backfill.get, **params)

        #......................................................................
        # Test all the backfill functions
        self.setup_data()
        for test, data in self.test_source_data.items():
            data['params']['backfill_type'] = str(test)
            res = backfill.get(**data['params'])
            self.assertEqual(res[0], data['res_expected'][0])
