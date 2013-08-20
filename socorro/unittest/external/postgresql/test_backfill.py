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

            for rows in table.generate_rows():
                data = dict(zip(table_columns, rows))
                query = "INSERT INTO %(table)s " % {'table': table_name}
                query = query + columns.replace("'", "").replace(",)", ")")
                query = query + " VALUES "
                query = query + values.replace(",)", ")").replace("'", "")

                cursor.execute(query, data)
                self.connection.commit()

                # TODO: insert a single line in os_versions table because
                # backfill_reports_clean() sometimes tries to insert a
                # os_version_id that already exists
                if table.columns == "os_versions":
                    break

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
            # Test 1: backfill_adu
            'adu': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 2: backfill_all_dups
            'all_dups': {
                'params': {
                    "start_date": yesterday_str,
                    "end_date": now_str,
                },
                'res_expected': [(True,)],
            },
            # Test 3: backfill_build_adu
            'build_adu': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 4: backfill_correlations
            'correlations': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 5: backfill_crashes_by_user_build
            'crashes_by_user_build': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 6: backfill_crashes_by_user
            'crashes_by_user': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },

            # TODO: Test 7: backfill_daily_crashes tries to insert into a table
            # that do not exists. It can be fixed by creating a temporary one.
            #'daily_crashes': {
            #    'params': {
            #        "update_day": now_str,
            #    },
            #    'res_expected': [(True,)],
            # },

            # Test 8: backfill_exploitability
            'exploitability': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 9: backfill_explosiveness
            'explosiveness': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 10: backfill_hang_report
            'hang_report': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 11: backfill_home_page_graph_build
            'home_page_graph_build': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 12: backfill_home_page_graph
            'home_page_graph': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 13: backfill_matviews
            'matviews': {
                'params': {
                    "start_date": yesterday_str,
                    "end_date": now_str,
                    "reports_clean": 'false',
                },
                'res_expected': [(True,)],
            },
            # Test 14: backfill_nightly_builds
            'nightly_builds': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 15: backfill_one_day
            'one_day': {
                'params': {
                    "update_day": now_str,
                },
                'res_expected': [('done',)],
            },
            # Test 16: backfill_rank_compare
            'rank_compare': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 17: backfill_reports_clean
            'reports_clean': {
                'params': {
                    "start_date": yesterday_str,
                    "end_date": now_str,
                },
                'res_expected': [(True,)],
            },

            # TODO: Test 18: backfill_reports_duplicates tries to insert into a
            # table that do not exists. It can be fixed by using the update
            # function inside of the backfill.
            #'reports_duplicates': {
            #    'params': {
            #        "start_date": yesterday_str,
            #        "end_date": now_str,
            #    },
            #    'res_expected': [(True,)],
            # },

            # TODO: Test 19: backfill_signature_counts tries to insert into
            # tables and to update functions that does not exist.
            #'signature_counts': {
            #    'params': {
            #        "start_date": yesterday_str,
            #        "end_date": now_str,
            #    },
            #    'res_expected': [(True,)],
            # },

            # Test 20: backfill_signature_summary
            'signature_summary': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 21: backfill_tcbs_build
            'tcbs_build': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 22: backfill_tcbs
            'tcbs': {
                'params': {
                    "update_day": yesterday_str,
                },
                'res_expected': [(True,)],
            },
            # Test 23: backfill_weekly_report_partitions
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
