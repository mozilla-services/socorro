import unittest
import mock

import urllib2

from configman import Namespace, ConfigurationManager

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

class TestPostgresCrashStorage(unittest.TestCase):
    """
    Tests where the urllib part is mocked.
    """

    def test_success(self):
        mock_logging = mock.Mock()
        required_config = ElasticSearchCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'submission_url': 'http://elasticsearch_host/%s'
          }]
        )

        with config_manager.context() as config:
            es_storage = ElasticSearchCrashStorage(config)
            urllib_str = 'socorro.external.elasticsearch.crashstorage.urllib2'
            m_request = mock.Mock()
            m_urlopen = mock.Mock()
            with mock.patch(urllib_str) as mocked_urllib:
                mocked_urllib.Request = m_request
                m_request.return_value = 17
                mocked_urllib.urlopen = m_urlopen

                es_storage.save_processed(a_processed_crash)

                expected_request_args = (
                  'http://elasticsearch_host/9120408936ce666-ff3b-4c7a-9674-'
                                             '367fe2120408',
                  {},
                )
                m_request.assert_called_with(*expected_request_args)
                expected_urlopen_args = (17,)
                expected_urlopen_kwargs = {'timeout': 2}
                m_urlopen.assert_called_with(*expected_urlopen_args,
                                             **expected_urlopen_kwargs)

    def test_failure_no_retry(self):
        mock_logging = mock.Mock()
        required_config = ElasticSearchCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'submission_url': 'http://elasticsearch_host/%s'
          }]
        )

        with config_manager.context() as config:
            es_storage = ElasticSearchCrashStorage(config)
            urllib_str = 'socorro.external.elasticsearch.crashstorage.urllib2'
            m_request = mock.Mock()
            m_urlopen = mock.Mock()
            with mock.patch(urllib_str) as mocked_urllib:
                mocked_urllib.Request = m_request
                m_request.return_value = 17
                mocked_urllib.urlopen = m_urlopen
                failure_exception = Exception('horrors')
                m_urlopen.side_effect = failure_exception

                self.assertRaises(Exception,
                                  es_storage.save_processed,
                                  a_processed_crash)

                expected_request_args = (
                  'http://elasticsearch_host/9120408936ce666-ff3b-4c7a-9674-'
                                             '367fe2120408',
                  {},
                )
                m_request.assert_called_with(*expected_request_args)
                expected_urlopen_args = (17,)
                expected_urlopen_kwargs = {'timeout': 2}
                m_urlopen.assert_called_with(*expected_urlopen_args,
                                             **expected_urlopen_kwargs)


    def test_failure_limited_retry(self):
        mock_logging = mock.Mock()
        required_config = ElasticSearchCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'submission_url': 'http://elasticsearch_host/%s',
            'timeout': 0,
            'backoff_delays': [0, 0, 0],
            'transaction_executor_class': TransactionExecutorWithLimitedBackoff
          }]
        )

        with config_manager.context() as config:
            es_storage = ElasticSearchCrashStorage(config)
            urllib_str = 'socorro.external.elasticsearch.crashstorage.urllib2'
            m_request = mock.Mock()
            m_urlopen = mock.Mock()
            with mock.patch(urllib_str) as mocked_urllib:
                mocked_urllib.Request = m_request
                m_request.return_value = 17
                mocked_urllib.urlopen = m_urlopen

                failure_exception = urllib2.socket.timeout
                m_urlopen.side_effect = failure_exception

                self.assertRaises(urllib2.socket.timeout,
                                  es_storage.save_processed,
                                  a_processed_crash)

                expected_request_args = (
                  'http://elasticsearch_host/9120408936ce666-ff3b-4c7a-9674-'
                                             '367fe2120408',
                  {},
                )
                m_request.assert_called_with(*expected_request_args)
                self.assertEqual(m_urlopen.call_count, 3)
                expected_urlopen_args = (17,)
                expected_urlopen_kwargs = {'timeout': 0}
                m_urlopen.assert_called_with(*expected_urlopen_args,
                                             **expected_urlopen_kwargs)



    def test_success_after_limited_retry(self):
        mock_logging = mock.Mock()
        required_config = ElasticSearchCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'submission_url': 'http://elasticsearch_host/%s',
            'timeout': 0,
            'backoff_delays': [0, 0, 0],
            'transaction_executor_class': TransactionExecutorWithLimitedBackoff
          }]
        )

        with config_manager.context() as config:
            es_storage = ElasticSearchCrashStorage(config)
            urllib_str = 'socorro.external.elasticsearch.crashstorage.urllib2'
            m_request = mock.Mock()
            m_urlopen = mock.Mock()
            with mock.patch(urllib_str) as mocked_urllib:
                mocked_urllib.Request = m_request
                m_request.return_value = 17
                mocked_urllib.urlopen = m_urlopen

                urlopen_results = [urllib2.socket.timeout,
                                   urllib2.socket.timeout]
                def urlopen_fn(*args, **kwargs):
                    try:
                        r = urlopen_results.pop(0)
                        raise r
                    except IndexError:
                        return m_urlopen

                m_urlopen.side_effect = urlopen_fn

                es_storage.save_processed(a_processed_crash)

                expected_request_args = (
                  'http://elasticsearch_host/9120408936ce666-ff3b-4c7a-9674-'
                                             '367fe2120408',
                  {},
                )
                m_request.assert_called_with(*expected_request_args)
                self.assertEqual(m_urlopen.call_count, 3)
                expected_urlopen_args = (17,)
                expected_urlopen_kwargs = {'timeout': 0}
                m_urlopen.assert_called_with(*expected_urlopen_args,
                                             **expected_urlopen_kwargs)



