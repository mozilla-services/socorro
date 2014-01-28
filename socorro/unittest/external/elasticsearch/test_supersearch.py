# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import mock
from nose.plugins.attrib import attr

from configman import ConfigurationManager, Namespace

from socorro.external import BadArgumentError
from socorro.external.elasticsearch import crashstorage
from socorro.external.elasticsearch.supersearch import SuperSearch
from socorro.lib import datetimeutil, search_common
from .unittestbase import ElasticSearchTestCase

# Remove debugging noise during development
# import logging
# logging.getLogger('pyelasticsearch').setLevel(logging.ERROR)
# logging.getLogger('elasticutils').setLevel(logging.ERROR)
# logging.getLogger('requests.packages.urllib3.connectionpool')\
#        .setLevel(logging.ERROR)


def _get_config_manager(config, es_index=None):
    if not es_index:
        es_index = config.elasticsearch_index

    mock_logging = mock.Mock()

    required_config = \
        crashstorage.ElasticSearchCrashStorage.get_required_config()
    required_config.add_option('logger', default=mock_logging)

    webapi = Namespace()
    webapi.elasticsearch_index = es_index
    webapi.timeout = 2
    webapi.search_default_date_range = 7

    for opt in [
        'elasticSearchHostname',
        'elasticSearchPort',
        'elasticsearch_doctype',
        'elasticsearch_timeout',
        'facets_max_number',
        'searchMaxNumberOfDistinctSignatures',
        'platforms',
        'non_release_channels',
        'restricted_channels',
    ]:
        webapi[opt] = config.get(opt)

    required_config.webapi = webapi

    elasticsearch_url = 'http://' + config.elasticSearchHostname + ':9200'

    config_manager = ConfigurationManager(
        [required_config],
        app_name='testapp',
        app_version='1.0',
        app_description='app description',
        values_source_list=[{
            'logger': mock_logging,
            'elasticsearch_index': es_index,
            'elasticsearch_urls': elasticsearch_url,
            'backoff_delays': [1, 2],
        }],
        argv_source=[]
    )

    return config_manager


class TestSuperSearch(ElasticSearchTestCase):
    """Test SuperSearch's behavior with a mocked elasticsearch database. """

    def test_get_indexes(self):
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        now = datetime.datetime(2000, 2, 1, 0, 0)
        lastweek = now - datetime.timedelta(weeks=1)
        lastmonth = now - datetime.timedelta(weeks=4)

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastweek, '>'),
        ]

        res = api.get_indexes(dates)
        self.assertEqual(res, ['socorro_integration_test'])

        with _get_config_manager(self.config, es_index='socorro_%Y%W') \
            .context() as config:
            api = SuperSearch(config)

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastweek, '>'),
        ]

        res = api.get_indexes(dates)
        self.assertEqual(res, ['socorro_200004', 'socorro_200005'])

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastmonth, '>'),
        ]

        res = api.get_indexes(dates)
        self.assertEqual(
            res,
            [
                'socorro_200001', 'socorro_200002', 'socorro_200003',
                'socorro_200004', 'socorro_200005'
            ]
        )


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestSuperSearch(ElasticSearchTestCase):
    """Test SuperSearch with an elasticsearch database containing fake data.
    """

    def setUp(self):
        super(IntegrationTestSuperSearch, self).setUp()

        with _get_config_manager(self.config).context() as config:
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
            'address': '0x0',
            'signature': 'js::break_your_browser',
            'date_processed': yesterday,
            'product': 'WaterWolf',
            'version': '1.0',
            'release_channel': 'release',
            'os_name': 'Linux',
            'build': 1234567890,
            'reason': 'MOZALLOC_WENT_WRONG',
            'hangid': None,
            'process_type': None,
            'email': 'example@gmail.com',
            'url': 'https://mozilla.org',
            'user_comments': '',
            'install_age': 0,
        }
        default_raw_crash_report = {
            'Accessibility': True,
            'AvailableVirtualMemory': 10211743,
            'B2G_OS_Version': '1.1.203448',
            'BIOS_Manufacturer': 'SUSA',
            'IsGarbageCollecting': False,
            'Vendor': 'mozilla',
            'useragent_locale': 'en-US',
        }

        self.storage.save_raw_and_processed(
            default_raw_crash_report,
            None,
            default_crash_report,
            default_crash_report['uuid']
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, Accessibility=False),
            None,
            dict(default_crash_report, uuid=1, product='EarthRaccoon'),
            1
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, AvailableVirtualMemory=0),
            None,
            dict(default_crash_report, uuid=2, version='2.0'),
            2
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, B2G_OS_Version='1.3'),
            None,
            dict(default_crash_report, uuid=3, release_channel='aurora'),
            3
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, BIOS_Manufacturer='aidivn'),
            None,
            dict(default_crash_report, uuid=4, os_name='Windows NT'),
            4
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, IsGarbageCollecting=True),
            None,
            dict(default_crash_report, uuid=5, build=987654321),
            5
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, Vendor='gnusmas'),
            None,
            dict(default_crash_report, uuid=6, reason='VERY_BAD_EXCEPTION'),
            6
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, useragent_locale='fr'),
            None,
            dict(default_crash_report, uuid=7, hangid=12),
            7
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, Android_Model='PediaMad 17 Heavy'),
            None,
            dict(default_crash_report, uuid=8, process_type='plugin'),
            8
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

        self.storage.save_processed(
            dict(default_crash_report, uuid=13, email='example@hotmail.com')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=14, email='sauron@yahoo.com')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=15, email='sauron@mordor.info')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=16, install_age=87234)
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=17, url='http://www.mozilla.org')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=18, url='http://www.example.com')
        )

        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=19,
                user_comments='I love WaterWolf',
            )
        )

        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=20,
                user_comments='WaterWolf is so bad',
            )
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=21, address='0xa2e4509ca0')
        )

        # As indexing is asynchronous, we need to force elasticsearch to
        # make the newly created content searchable before we run the tests
        self.storage.es.refresh()

    def tearDown(self):
        # clear the test index
        with _get_config_manager(self.config).context() as config:
            self.storage.es.delete_index(config.webapi.elasticsearch_index)

    def test_get(self):
        """Test a search with default values returns the right structure. """
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        res = api.get()

        self.assertTrue('total' in res)
        self.assertEqual(res['total'], 21)

        self.assertTrue('hits' in res)
        self.assertEqual(len(res['hits']), res['total'])

        self.assertTrue('facets' in res)
        self.assertTrue('signature' in res['facets'])

        expected_signatures = [
            {'term': 'js::break_your_browser', 'count': 20},
            {'term': 'my_bad', 'count': 1},
        ]
        self.assertEqual(res['facets']['signature'], expected_signatures)

        # Test fields are being renamed
        self.assertTrue('date' in res['hits'][0])  # date_processed > date
        self.assertTrue('build_id' in res['hits'][0])  # build > build_id
        self.assertTrue('platform' in res['hits'][0])  # os_name > platform

    def test_get_individual_filters(self):
        """Test a search with single filters returns expected results. """
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        # Test signature
        args = {
            'signature': 'my_bad',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'my_bad')

        # Test product
        args = {
            'product': 'EarthRaccoon',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['product'], 'EarthRaccoon')

        # Test version
        args = {
            'version': '2.0',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['version'], '2.0')

        # Test release_channel
        args = {
            'release_channel': 'aurora',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['release_channel'], 'aurora')

        # Test platform
        args = {
            'platform': 'Windows',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['platform'], 'Windows NT')

        # Test build_id
        args = {
            'build_id': '987654321',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['build_id'], 987654321)

        # Test reason
        args = {
            'reason': 'MOZALLOC_WENT_WRONG',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertEqual(res['hits'][0]['reason'], 'MOZALLOC_WENT_WRONG')

        args = {
            'reason': ['very_bad_exception'],
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['reason'], 'VERY_BAD_EXCEPTION')

        # Test process_type
        args = {
            'process_type': 'plugin',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 3)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['process_type'], 'plugin')

        # Test url
        args = {
            'url': 'https://mozilla.org',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 19)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertTrue('mozilla.org' in res['hits'][0]['url'])

        # Test user_comments
        args = {
            'user_comments': 'WaterWolf',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 2)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertTrue('WaterWolf' in res['hits'][0]['user_comments'])

        # Test address
        args = {
            'address': '0x0',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue('0x0' in res['hits'][0]['address'])

        # Test accessibility
        args = {
            'accessibility': False,
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertTrue(not res['hits'][0]['accessibility'])

        args = {
            'accessibility': 'True',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 8)
        self.assertTrue(res['hits'][0]['accessibility'])

        # Test b2g_os_version
        args = {
            'b2g_os_version': '1.3',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['b2g_os_version'], '1.3')

        # Test bios_manufacturer
        args = {
            'bios_manufacturer': 'aidivn',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['bios_manufacturer'], 'aidivn')

        # Test is_garbage_collecting
        args = {
            'is_garbage_collecting': True,
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertTrue(res['hits'][0]['is_garbage_collecting'])

        # Test vendor
        args = {
            'vendor': 'gnusmas',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['vendor'], 'gnusmas')

        # Test useragent_locale
        args = {
            'useragent_locale': 'fr',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['useragent_locale'], 'fr')

    def test_get_with_range_operators(self):
        """Test a search with several filters and operators returns expected
        results. """
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        # Test date
        now = datetimeutil.utc_now()
        lastweek = now - datetime.timedelta(days=7)
        lastmonth = lastweek - datetime.timedelta(weeks=4)
        args = {
            'date': [
                '<%s' % lastweek,
                '>=%s' % lastmonth,
            ]
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'my_little_signature')

        # Test build id
        args = {
            'build_id': '<1234567890',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertTrue(res['hits'][0]['build_id'] < 1234567890)

        args = {
            'build_id': '>1234567889',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertTrue(report['build_id'] > 1234567889)

        args = {
            'build_id': '<=1234567890',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 21)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertTrue(report['build_id'] <= 1234567890)

        # Test available_virtual_memory
        args = {
            'available_virtual_memory': '>=1',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 8)
        for report in res['hits']:
            self.assertTrue(report['available_virtual_memory'] >= 1)

        args = {
            'available_virtual_memory': '<1',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['available_virtual_memory'], 0)

    def test_get_with_string_operators(self):
        """Test a search with several filters and operators returns expected
        results. """
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        # Test signature
        args = {
            'signature': ['js', 'break_your_browser'],
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertEqual(report['signature'], 'js::break_your_browser')

        # - Test contains mode
        args = {
            'signature': '~bad',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'my_bad')

        args = {
            'signature': '~js::break',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertEqual(report['signature'], 'js::break_your_browser')

        # - Test is_exactly mode
        args = {
            'signature': '=js::break_your_browser',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertEqual(report['signature'], 'js::break_your_browser')

        args = {
            'signature': '=my_bad',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'my_bad')

        # - Test starts_with mode
        args = {
            'signature': '$js',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertEqual(report['signature'], 'js::break_your_browser')

        # - Test ends_with mode
        args = {
            'signature': '^browser',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertEqual(report['signature'], 'js::break_your_browser')

        # Test email
        args = {
            'email': 'sauron@mordor.info',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertTrue(res['hits'])
        self.assertEqual(res['hits'][0]['email'], 'sauron@mordor.info')

        args = {
            'email': '~mail.com',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 19)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertTrue('@' in report['email'])
            self.assertTrue('mail.com' in report['email'])

        args = {
            'email': '$sauron@',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 2)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertTrue('sauron@' in report['email'])

        # Test url
        args = {
            'url': 'https://mozilla.org',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 19)

        args = {
            'url': '~mozilla.org',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertTrue('mozilla.org' in report['url'])

        args = {
            'url': '^.com',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['url'], 'http://www.example.com')

        # Test user_comments
        args = {
            'user_comments': '~love',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(res['hits'][0]['user_comments'], 'I love WaterWolf')

        args = {
            'user_comments': '$WaterWolf',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertEqual(
            res['hits'][0]['user_comments'],
            'WaterWolf is so bad'
        )

        args = {
            'user_comments': '__null__',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 19)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        for hit in res['hits']:
            self.assertEqual(hit['user_comments'], '')

        # Test address
        args = {
            'address': '^0',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 21)
        args = {
            'address': '~a2',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)

        # Test android_model
        args = {
            'android_model': '~PediaMad',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)

        args = {
            'android_model': '=PediaMad 17 Heavy',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)

    def test_get_with_facets(self):
        """Test a search with facets returns expected results. """
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        # Test several facets
        args = {
            '_facets': ['signature', 'platform']
        }
        res = api.get(**args)

        self.assertTrue('facets' in res)
        self.assertTrue('signature' in res['facets'])

        expected_signatures = [
            {'term': 'js::break_your_browser', 'count': 20},
            {'term': 'my_bad', 'count': 1},
        ]
        self.assertEqual(res['facets']['signature'], expected_signatures)

        self.assertTrue('platform' in res['facets'])
        expected_platforms = [
            {'term': 'Linux', 'count': 20},
            {'term': 'Windows NT', 'count': 1},
        ]
        self.assertEqual(res['facets']['platform'], expected_platforms)

        # Test one facet with filters
        args = {
            '_facets': ['release_channel'],
            'release_channel': 'aurora',
        }
        res = api.get(**args)

        self.assertTrue('release_channel' in res['facets'])

        expected_signatures = [
            {'term': 'aurora', 'count': 1},
        ]
        self.assertEqual(res['facets']['release_channel'], expected_signatures)

        # Test one facet with a different filter
        args = {
            '_facets': ['release_channel'],
            'platform': 'linux',
        }
        res = api.get(**args)

        self.assertTrue('release_channel' in res['facets'])

        expected_signatures = [
            {'term': 'release', 'count': 19},
            {'term': 'aurora', 'count': 1},
        ]
        self.assertEqual(res['facets']['release_channel'], expected_signatures)

        # Test errors
        self.assertRaises(
            BadArgumentError,
            api.get,
            _facets=['unkownfield']
        )

    def test_get_with_pagination(self):
        """Test a search with pagination returns expected results. """
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        args = {
            '_results_number': '10',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 21)
        self.assertEqual(len(res['hits']), 10)

        args = {
            '_results_number': '10',
            '_results_offset': '10',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 21)
        self.assertEqual(len(res['hits']), 10)

        args = {
            '_results_number': '10',
            '_results_offset': '15',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 21)
        self.assertEqual(len(res['hits']), 6)

        args = {
            '_results_number': '10',
            '_results_offset': '30',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 21)
        self.assertEqual(len(res['hits']), 0)

    def test_get_with_not_operator(self):
        """Test a search with a few NOT operators. """
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        # Test signature
        args = {
            'signature': ['js', 'break_your_browser'],
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertEqual(report['signature'], 'js::break_your_browser')

        # - Test contains mode
        args = {
            'signature': '!~bad',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)

        # - Test is_exactly mode
        args = {
            'signature': '!=js::break_your_browser',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'my_bad')

        # - Test starts_with mode
        args = {
            'signature': '!$js',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'my_bad')

        # - Test ends_with mode
        args = {
            'signature': '!^browser',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'my_bad')

        # Test build id
        args = {
            'build_id': '!<1234567890',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 20)
        self.assertTrue(res['hits'])
        for report in res['hits']:
            self.assertTrue(report['build_id'] > 1234567889)

        args = {
            'build_id': '!>1234567889',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res['hits'][0]['signature'], 'js::break_your_browser')
        self.assertTrue(res['hits'][0]['build_id'] < 1234567890)

        args = {
            'build_id': '!<=1234567890',
        }
        res = api.get(**args)
        self.assertEqual(res['total'], 0)

    @mock.patch(
        'socorro.external.elasticsearch.supersearch.SuperSearch.get_indexes'
    )
    def test_list_of_indices(self, mocked_get_indexes):
        """Test that unexisting indices are handled correctly. """
        with _get_config_manager(self.config).context() as config:
            api = SuperSearch(config)

        mocked_get_indexes.return_value = ['socorro_unknown']

        res = api.get()
        res_expected = {
            'hits': [],
            'total': 0,
            'facets': {},
        }
        self.assertEqual(res, res_expected)

        mocked_get_indexes.return_value = [
            'socorro_integration_test',
            'something_that_does_not_exist',
            'another_one'
        ]

        res = api.get()

        self.assertTrue('total' in res)
        self.assertEqual(res['total'], 21)

        self.assertTrue('hits' in res)
        self.assertEqual(len(res['hits']), res['total'])

        self.assertTrue('facets' in res)
        self.assertTrue('signature' in res['facets'])
