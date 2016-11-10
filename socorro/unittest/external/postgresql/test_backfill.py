# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .unittestbase import PostgreSQLTestCase
from nose.tools import eq_, assert_raises
import datetime

from socorro.lib import MissingArgumentError, datetimeutil
from socorro.external.postgresql.backfill import Backfill
from socorro.external.postgresql import staticdata, fakedata


#==============================================================================
class TestBackfill(PostgreSQLTestCase):
    """Tests the calling of all backfill functions"""

    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate tables with fake data """
        super(TestBackfill, self).setUp()

        self.truncate_tables()

        cursor = self.connection.cursor()

        for table in staticdata.tables + fakedata.tables:
            # staticdata has no concept of duration
            if table.__module__ == 'socorro.external.postgresql.staticdata':
                table = table()
            else:
                table = table(days=1)
            table.releases = {
                'WaterWolf': {
                    'channels': {
                        'Nightly': {
                            'versions': [{
                                'number': '18.0',
                                'probability': 0.5,
                                'buildid': '%s000020'
                            }],
                            'adu': '10',
                            'repository': 'nightly',
                            'throttle': '1',
                            'update_channel': 'nightly',
                        },
                    },
                    'crashes_per_hour': '5',
                    'guid': '{waterwolf@example.com}'
                },
                'B2G': {
                    'channels': {
                        'Nightly': {
                            'versions': [{
                                'number': '18.0',
                                'probability': 0.5,
                                'buildid': '%s000020'
                            }],
                            'adu': '10',
                            'repository': 'nightly',
                            'throttle': '1',
                            'update_channel': 'nightly',
                        },
                    },
                    'crashes_per_hour': '5',
                    'guid': '{waterwolf@example.com}'
                }
            }

            table_name = table.table
            table_columns = table.columns
            values = str(tuple(["%(" + i + ")s" for i in table_columns]))
            columns = str(tuple(table_columns))

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
        self.truncate_tables()
        super(TestBackfill, self).tearDown()

    #--------------------------------------------------------------------------
    def truncate_tables(self):
        tables = []
        for table_class in staticdata.tables + fakedata.tables:
            tables.append(table_class().table)

        cursor = self.connection.cursor()
        tables = str(tables).replace("[", "").replace("]", "")
        cursor.execute("TRUNCATE " + tables.replace("'", "") + " CASCADE;")
        self.connection.commit()

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
            # TODO: Update Backfill to support signature_summary backfill
            # through the API
            #'signature_summary_products': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
            #'signature_summary_installations': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
            #'signature_summary_uptime': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
            #'signature_summary_os': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
            #'signature_summary_process_type': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
            #'signature_summary_architecture': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
            #'signature_summary_flash_version': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
            #'signature_summary_device': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
            #'signature_summary_graphics': {
            #    'params': {
            #        "update_day": yesterday_str,
            #    },
            #    'res_expected': [(True,)],
            #},
        }

    #--------------------------------------------------------------------------
    def test_get(self):

        backfill = Backfill(config=self.config)

        #......................................................................
        # Test raise error if kind of backfill is not passed
        params = {"backfill_type": ''}
        assert_raises(MissingArgumentError, backfill.get, **params)

        #......................................................................
        # Test all the backfill functions
        self.setup_data()
        for test, data in self.test_source_data.items():
            data['params']['backfill_type'] = str(test)
            res = backfill.get(**data['params'])
            eq_(res[0], data['res_expected'][0])
