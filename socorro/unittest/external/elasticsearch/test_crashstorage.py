# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock
import pyelasticsearch

from configman import ConfigurationManager

from socorro.external.elasticsearch.crashstorage import (
    ElasticSearchCrashStorage
)
from socorro.database.transaction_executor import (
    TransactionExecutorWithLimitedBackoff
)


a_processed_crash = {
    "addons": [["{1a5dabbd-0e74-41da-b532-a364bb552cab}", "1.0.4.1"]],
    "addons_checked": None,
    "address": "0x1c",
    "app_notes": "...",
    "build": "20120309050057",
    "client_crash_date": "2012-04-08 10:52:42.0",
    "completeddatetime": "2012-04-08 10:56:50.902884",
    "cpu_info": "None | 0",
    "cpu_name": "arm",
    "crashedThread": 8,
    "date_processed": "2012-04-08 10:56:41.558922",
    "distributor": None,
    "distributor_version": None,
    "dump": "...",
    "email": "bogus@bogus.com",
    "flash_version": "[blank]",
    "hangid": None,
    "id": 361399767,
    "install_age": 22385,
    "last_crash": None,
    "os_name": "Linux",
    "os_version": "0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ",
    "processor_notes": "SignatureTool: signature truncated due to length",
    "process_type": "plugin",
    "product": "FennecAndroid",
    "PluginFilename": "dwight.txt",
    "PluginName": "wilma",
    "PluginVersion": "69",
    "reason": "SIGSEGV",
    "release_channel": "default",
    "ReleaseChannel": "default",
    "signature": "libxul.so@0x117441c",
    "startedDateTime": "2012-04-08 10:56:50.440752",
    "success": True,
    "topmost_filenames": [],
    "truncated": False,
    "uptime": 170,
    "url": "http://embarasing.porn.com",
    "user_comments": None,
    "user_id": None,
    "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
    "version": "13.0a1",
}


a_raw_crash = {
    "foo": "alpha",
    "bar": 42,
}


class TestElasticsearchCrashStorage(unittest.TestCase):

    @mock.patch('socorro.external.elasticsearch.crashstorage.pyelasticsearch')
    def test_indexing(self, pyes_mock):
        mock_logging = mock.Mock()
        mock_es = mock.Mock()
        pyes_mock.exceptions.ElasticHttpNotFoundError = \
            pyelasticsearch.exceptions.ElasticHttpNotFoundError

        pyes_mock.ElasticSearch.return_value = mock_es
        required_config = ElasticSearchCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{
                'logger': mock_logging,
                'elasticsearch_urls': 'http://elasticsearch_host:9200',
            }]
        )

        with config_manager.context() as config:
            es_storage = ElasticSearchCrashStorage(config)
            crash_report = a_processed_crash.copy()
            crash_report['date_processed'] = '2013-01-01 10:56:41.558922'

            def status_fn(index):
                assert 'socorro20130' in index
                if index == 'socorro201300':
                    raise pyelasticsearch.exceptions.ElasticHttpNotFoundError()

            mock_es.status = status_fn

            # The index does not exist and is created
            es_storage.save_processed(crash_report)
            self.assertEqual(mock_es.create_index.call_count, 1)

            # The index exists and is not created
            crash_report['date_processed'] = '2013-01-10 10:56:41.558922'
            es_storage.save_processed(crash_report)

            self.assertEqual(mock_es.create_index.call_count, 1)

    @mock.patch('socorro.external.elasticsearch.crashstorage.pyelasticsearch')
    def test_success(self, pyes_mock):
        mock_logging = mock.Mock()
        mock_es = mock.Mock()

        pyes_mock.ElasticSearch.return_value = mock_es
        required_config = ElasticSearchCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{
                'logger': mock_logging,
                'elasticsearch_urls': 'http://elasticsearch_host:9200',
            }]
        )

        with config_manager.context() as config:
            crash_id = a_processed_crash['uuid']

            es_storage = ElasticSearchCrashStorage(config)
            es_storage.save_raw_and_processed(
                a_raw_crash,
                None,
                a_processed_crash.copy(),
                crash_id,
            )

            expected_crash = {
                'crash_id': crash_id,
                'processed_crash': a_processed_crash.copy(),
                'raw_crash': a_raw_crash
            }

            expected_request_args = (
                'socorro201214',
                'crash_reports',
                expected_crash
            )
            expected_request_kwargs = {
                'id': crash_id,
                'replication': 'async',
            }

            mock_es.index.assert_called_with(
                *expected_request_args,
                **expected_request_kwargs
            )

    @mock.patch('socorro.external.elasticsearch.crashstorage.pyelasticsearch')
    def test_failure_no_retry(self, pyes_mock):
        mock_logging = mock.Mock()
        mock_es = mock.Mock()

        pyes_mock.ElasticSearch.return_value = mock_es
        required_config = ElasticSearchCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{
                'logger': mock_logging,
                'elasticsearch_urls': 'http://elasticsearch_host:9200',
            }]
        )

        with config_manager.context() as config:
            es_storage = ElasticSearchCrashStorage(config)

            failure_exception = Exception('horrors')
            mock_es.index.side_effect = failure_exception

            crash_id = a_processed_crash['uuid']

            self.assertRaises(
                Exception,
                es_storage.save_raw_and_processed,
                a_raw_crash,
                None,
                a_processed_crash.copy(),
                crash_id,
            )

            expected_crash = {
                'crash_id': crash_id,
                'processed_crash': a_processed_crash.copy(),
                'raw_crash': a_raw_crash
            }

            expected_request_args = (
                'socorro201214',
                'crash_reports',
                expected_crash
            )
            expected_request_kwargs = {
                'replication': 'async',
                'id': crash_id,
            }

            mock_es.index.assert_called_with(
                *expected_request_args,
                **expected_request_kwargs
            )

    @mock.patch('socorro.external.elasticsearch.crashstorage.pyelasticsearch')
    def test_failure_limited_retry(self, pyes_mock):
        mock_logging = mock.Mock()
        mock_es = mock.Mock()

        pyes_mock.ElasticSearch.return_value = mock_es
        required_config = ElasticSearchCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{
                'logger': mock_logging,
                'elasticsearch_urls': 'http://elasticsearch_host:9200',
                'timeout': 0,
                'backoff_delays': [0, 0, 0],
                'transaction_executor_class':
                    TransactionExecutorWithLimitedBackoff
            }]
        )

        with config_manager.context() as config:
            es_storage = ElasticSearchCrashStorage(config)

            failure_exception = pyelasticsearch.exceptions.Timeout
            mock_es.index.side_effect = failure_exception

            crash_id = a_processed_crash['uuid']

            self.assertRaises(
                pyelasticsearch.exceptions.Timeout,
                es_storage.save_raw_and_processed,
                a_raw_crash,
                None,
                a_processed_crash.copy(),
                crash_id,
            )

            expected_crash = {
                'crash_id': crash_id,
                'processed_crash': a_processed_crash.copy(),
                'raw_crash': a_raw_crash
            }

            expected_request_args = (
                'socorro201214',
                'crash_reports',
                expected_crash
            )
            expected_request_kwargs = {
                'replication': 'async',
                'id': crash_id,
            }

            mock_es.index.assert_called_with(
                *expected_request_args,
                **expected_request_kwargs
            )

    @mock.patch('socorro.external.elasticsearch.crashstorage.pyelasticsearch')
    def test_success_after_limited_retry(self, pyes_mock):
        mock_logging = mock.Mock()
        mock_es = mock.Mock()

        pyes_mock.ElasticSearch.return_value = mock_es
        required_config = ElasticSearchCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{
                'logger': mock_logging,
                'elasticsearch_urls': 'http://elasticsearch_host:9200',
                'timeout': 0,
                'backoff_delays': [0, 0, 0],
                'transaction_executor_class':
                    TransactionExecutorWithLimitedBackoff
            }]
        )

        with config_manager.context() as config:
            es_storage = ElasticSearchCrashStorage(config)

            esindex_results = [pyelasticsearch.exceptions.Timeout,
                               pyelasticsearch.exceptions.Timeout]

            def esindex_fn(*args, **kwargs):
                try:
                    r = esindex_results.pop(0)
                    raise r
                except IndexError:
                    return mock_es.index

            mock_es.index.side_effect = esindex_fn

            crash_id = a_processed_crash['uuid']

            es_storage.save_raw_and_processed(
                a_raw_crash,
                None,
                a_processed_crash.copy(),
                crash_id,
            )

            expected_crash = {
                'crash_id': crash_id,
                'processed_crash': a_processed_crash.copy(),
                'raw_crash': a_raw_crash
            }

            expected_request_args = (
                'socorro201214',
                'crash_reports',
                expected_crash
            )
            expected_request_kwargs = {
                'replication': 'async',
                'id': crash_id,
            }

            mock_es.index.assert_called_with(
                *expected_request_args,
                **expected_request_kwargs
            )
