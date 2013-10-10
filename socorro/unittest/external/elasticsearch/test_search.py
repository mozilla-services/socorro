# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import mock
import unittest
from nose.plugins.attrib import attr

from configman import ConfigurationManager, Namespace
from .unittestbase import ElasticSearchTestCase

from socorro.external.elasticsearch import crashstorage
from socorro.external.elasticsearch.search import Search
from socorro.lib import util, datetimeutil


#==============================================================================
class TestElasticSearchSearch(unittest.TestCase):
    """Test Search class implemented with ElasticSearch. """

    #--------------------------------------------------------------------------
    def get_dummy_context(self):
        """
        Create a dummy config object to use when testing.
        """
        context = util.DotDict()
        context.elasticSearchHostname = ""
        context.elasticSearchPort = 9200
        context.platforms = (
            {
                "id": "windows",
                "name": "Windows NT"
            },
            {
                "id": "linux",
                "name": "Linux"
            }
        )
        return context

    #--------------------------------------------------------------------------
    def test_get_signatures_list(self):
        """
        Test Search.get_signatures()
        """
        context = self.get_dummy_context()
        facets = {
            "signatures": {
                "terms": [
                    {
                        "term": "hang",
                        "count": 145
                    },
                    {
                        "term": "js",
                        "count": 7
                    },
                    {
                        "term": "ws",
                        "count": 4
                    }
                ]
            }
        }
        size = 3
        expected = ["hang", "js", "ws"]
        signatures = Search.get_signatures_list(
            facets,
            size,
            context.platforms
        )
        res_signs = []
        for sign in signatures:
            self.assertTrue(sign["signature"] in expected)
            res_signs.append(sign["signature"])

        for sign in expected:
            self.assertTrue(sign in res_signs)

    #--------------------------------------------------------------------------
    def test_get_counts(self):
        """
        Test Search.get_counts()
        """
        context = self.get_dummy_context()
        signatures = [
            {
                "signature": "hang",
                "count": 12
            },
            {
                "signature": "js",
                "count": 4
            }
        ]
        count_sign = {
            "hang": {
                "terms": [
                    {
                        "term": "windows",
                        "count": 3
                    },
                    {
                        "term": "linux",
                        "count": 4
                    }
                ]
            },
            "js": {
                "terms": [
                    {
                        "term": "windows",
                        "count": 2
                    }
                ]
            },
            "hang_hang": {
                "count": 0
            },
            "js_hang": {
                "count": 0
            },
            "hang_plugin": {
                "count": 0
            },
            "js_plugin": {
                "count": 0
            },
            "hang_content": {
                "count": 0
            },
            "js_content": {
                "count": 0
            }
        }
        res = Search.get_counts(
            signatures,
            count_sign,
            0,
            2,
            context.platforms
        )

        self.assertTrue(type(res) is list)
        for sign in res:
            self.assertTrue("signature" in sign)
            self.assertTrue("count" in sign)
            self.assertTrue("is_windows" in sign)
            self.assertTrue("numhang" in sign)
            self.assertTrue("numplugin" in sign)
            self.assertTrue("numcontent" in sign)

        self.assertTrue("is_linux" in res[0])
        self.assertFalse("is_linux" in res[1])


#==============================================================================
@attr(integration='elasticsearch')
class IntegrationElasticsearchSearch(ElasticSearchTestCase):
    """Test search with an elasticsearch database containing fake data. """

    def setUp(self):
        super(IntegrationElasticsearchSearch, self).setUp()

        with self.get_config_manager().context() as config:
            self.storage = crashstorage.ElasticSearchCrashStorage(config)

            # clear the indices cache so the index is created on every test
            self.storage.indices_cache = set()

        now = datetimeutil.utc_now()

        yesterday = now - datetime.timedelta(days=1)
        yesterday = datetimeutil.date_to_string(yesterday)

        last_month = now - datetime.timedelta(weeks=4)
        last_month = datetimeutil.date_to_string(last_month)

        # insert data into elasticsearch
        default_crash_report = {
            'uuid': 100,
            'signature': 'js::break_your_browser',
            'date_processed': yesterday,
            'product': 'WaterWolf',
            'version': '1.0',
            'release_channel': 'release',
            'os_name': 'Linux',
            'build': '1234567890',
            'reason': 'MOZALLOC_WENT_WRONG',
            'hangid': None,
            'process_type': None,
        }

        self.storage.save_processed(default_crash_report)

        self.storage.save_processed(
            dict(default_crash_report, uuid=1, product='EarthRaccoon')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=2, version='2.0')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=3, release_channel='aurora')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=4, os_name='Windows NT')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=5, build='0987654321')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=6, reason='VERY_BAD_EXCEPTION')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=7, hangid='12')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=8, process_type='plugin')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=9, signature='my_bad')
        )

        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=10,
                date_processed=last_month,
                signature='my_little_signature',
            )
        )

        # for plugin terms test
        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=11,
                product='PluginSoft',
                process_type='plugin',
                PluginFilename='carly.dll',
                PluginName='Hey I just met you',
                PluginVersion='1.2',
            )
        )

        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=12,
                product='PluginSoft',
                process_type='plugin',
                PluginFilename='hey.dll',
                PluginName='Hey Plugin',
                PluginVersion='10.7.0.2a',
            )
        )

        # As indexing is asynchronous, we need to force elasticsearch to
        # make the newly created content searchable before we run the tests
        self.storage.es.refresh()

    def tearDown(self):
        # clear the test index
        with self.get_config_manager().context() as config:
            self.storage.es.delete_index(config.webapi.elasticsearch_index)

    def get_config_manager(self):
        mock_logging = mock.Mock()

        required_config = \
            crashstorage.ElasticSearchCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        webapi = Namespace()
        webapi.timeout = 2

        for opt in [
            'elasticSearchHostname',
            'elasticSearchPort',
            'elasticsearch_index',
            'elasticsearch_doctype',
            'searchMaxNumberOfDistinctSignatures',
            'platforms',
            'channels',
            'restricted_channels',
        ]:
            webapi[opt] = self.config.get(opt)

        required_config.webapi = webapi

        urls = 'http://' + self.config.elasticSearchHostname + ':9200'

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{
                'logger': mock_logging,
                'elasticsearch_index': webapi.elasticsearch_index,
                'elasticsearch_urls': urls,
            }]
        )

        return config_manager

    @mock.patch('socorro.external.elasticsearch.search.Util')
    def test_search_single_filters(self, mock_psql_util):
        # verify results show expected numbers
        with self.get_config_manager().context() as config:
            api = Search(config=config)

            # test no filter, get all results
            params = {}
            res = api.get()

            self.assertEqual(res['total'], 2)
            self.assertEqual(
                res['hits'][0]['signature'],
                'js::break_your_browser'
            )
            self.assertEqual(
                res['hits'][1]['signature'],
                'my_bad'
            )
            self.assertEqual(res['hits'][0]['is_linux'], 10)
            self.assertEqual(res['hits'][0]['is_windows'], 1)
            self.assertEqual(res['hits'][0]['is_mac'], 0)

            # test product
            params = {
                'products': 'EarthRaccoon'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test version
            params = {
                'versions': 'WaterWolf:2.0'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test release_channel
            params = {
                'release_channels': 'aurora'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test os_name
            params = {
                'os': 'Windows'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test short os_name
            params = {
                'os': 'win'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test build
            params = {
                'build_ids': '0987654321'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test reason
            params = {
                'reasons': 'VERY_BAD_EXCEPTION'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test hangid
            params = {
                'report_type': 'hang'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test process_type
            params = {
                'report_process': 'plugin'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 3)

            # test signature
            params = {
                'terms': 'my_bad'
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

    @mock.patch('socorro.external.elasticsearch.search.Util')
    def test_search_combined_filters(self, mock_psql_util):
        with self.get_config_manager().context() as config:
            api = Search(config=config)

            # get the first, default crash report
            params = {
                'terms': 'js::break_your_browser',
                'search_mode': 'is_exactly',
                'products': 'WaterWolf',
                'versions': 'WaterWolf:1.0',
                'release_channels': 'release',
                'os': 'Linux',
                'build_ids': '1234567890',
                'reasons': 'MOZALLOC_WENT_WRONG',
                'report_type': 'crash',
                'report_process': 'browser',
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(
                res['hits'][0]['signature'],
                'js::break_your_browser'
            )
            self.assertEqual(res['hits'][0]['is_linux'], 1)
            self.assertEqual(res['hits'][0]['is_windows'], 0)
            self.assertEqual(res['hits'][0]['is_mac'], 0)

            # get the crash report from last month
            now = datetimeutil.utc_now()

            three_weeks_ago = now - datetime.timedelta(weeks=3)
            three_weeks_ago = datetimeutil.date_to_string(three_weeks_ago)

            five_weeks_ago = now - datetime.timedelta(weeks=5)
            five_weeks_ago = datetimeutil.date_to_string(five_weeks_ago)

            params = {
                'from_date': five_weeks_ago,
                'to_date': three_weeks_ago,
            }
            res = api.get(**params)

            self.assertEqual(res['total'], 1)
            self.assertEqual(
                res['hits'][0]['signature'],
                'my_little_signature'
            )
            self.assertEqual(res['hits'][0]['is_linux'], 1)
            self.assertEqual(res['hits'][0]['is_windows'], 0)
            self.assertEqual(res['hits'][0]['is_mac'], 0)

    @mock.patch('socorro.external.elasticsearch.search.Util')
    def test_search_no_results(self, mock_psql_util):
        with self.get_config_manager().context() as config:
            api = Search(config=config)

            # unexisting signature
            params = {
                'terms': 'callMeMaybe()',
            }
            res = api.get(**params)
            self.assertEqual(res['total'], 0)

            # unexisting product
            params = {
                'products': 'WindBear',
            }
            res = api.get(**params)
            self.assertEqual(res['total'], 0)

    @mock.patch('socorro.external.elasticsearch.search.Util')
    def test_search_plugin_terms(self, mock_psql_util):
        with self.get_config_manager().context() as config:
            api = Search(config=config)

            base_params = {
                'products': 'PluginSoft',
                'report_process': 'plugin',
            }

            # test 'is_exactly' mode
            base_params['plugin_search_mode'] = 'is_exactly'

            # get all results with filename being exactly 'carly.dll'
            # expect 1 signature with 1 crash
            params = dict(
                base_params,
                plugin_terms='carly.dll',
                plugin_in='filename',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # get all results with name being exactly 'Hey Plugin'
            # expect 1 signature with 1 crash
            params = dict(
                base_params,
                plugin_terms='Hey Plugin',
                plugin_in='name',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test 'contains' mode
            base_params['plugin_search_mode'] = 'contains'

            # get all results with filename containing '.dll'
            # expect 1 signature with 2 crashes
            params = dict(
                base_params,
                plugin_terms='.dll',
                plugin_in='filename',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 2)

            # get all results with name containing 'Hey'
            # expect 1 signature with 2 crashes
            params = dict(
                base_params,
                plugin_terms='Hey',
                plugin_in='name',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 2)

            # get all results with name containing 'Plugin'
            # expect 1 signature with 1 crash
            params = dict(
                base_params,
                plugin_terms='Plugin',
                plugin_in='name',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # test 'starts_with' mode
            base_params['plugin_search_mode'] = 'starts_with'

            # get all results with filename starting with 'car'
            # expect 1 signature with 1 crash
            params = dict(
                base_params,
                plugin_terms='car',
                plugin_in='filename',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # get all results with name starting with 'Hey'
            # expect 1 signature with 2 crashes
            params = dict(
                base_params,
                plugin_terms='Hey',
                plugin_in='name',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 2)

            # test 'default' mode
            base_params['plugin_search_mode'] = 'default'

            # get all results with name containing the word 'hey'
            # expect 1 signature with 2 crashes
            params = dict(
                base_params,
                plugin_terms='hey',
                plugin_in='name',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 2)

            # get all results with name containing the word 'you'
            # expect 1 signature with 1 crash
            params = dict(
                base_params,
                plugin_terms='you',
                plugin_in='name',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)
            self.assertEqual(res['hits'][0]['count'], 1)

            # Test return values
            res = api.get(**base_params)
            self.assertEqual(res['total'], 1)
            self.assertTrue('pluginname' in res['hits'][0])
            self.assertTrue('pluginfilename' in res['hits'][0])
            self.assertTrue('pluginversion' in res['hits'][0])

            params = dict(
                base_params,
                plugin_search_mode='is_exactly',
                plugin_terms='carly.dll',
                plugin_in='filename',
            )
            res = api.get(**params)
            self.assertEqual(res['total'], 1)

            hit = res['hits'][0]
            self.assertEqual(hit['pluginname'], 'Hey I just met you')
            self.assertEqual(hit['pluginfilename'], 'carly.dll')
            self.assertEqual(hit['pluginversion'], '1.2')
