# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch
import mock

from nose.tools import eq_, ok_, assert_raises

from copy import deepcopy

from configman.dotdict import DotDict

from socorro.external.crashstorage_base import Redactor
from socorro.external.es.crashstorage import (
    ESCrashStorage,
    ESCrashStorageRedactedSave,
    ESCrashStorageRedactedJsonDump,
    ESBulkCrashStorage,
    RawCrashRedactor,
)
from socorro.lib.datetimeutil import string_to_datetime
from socorro.unittest.external.es.base import (
    ElasticsearchTestCase,
    TestCaseWithConfig,
)


# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)


# A dummy crash report that is used for testing.
a_processed_crash = {
    'addons': [['{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1']],
    'addons_checked': None,
    'address': '0x1c',
    'app_notes': '...',
    'build': '20120309050057',
    'client_crash_date': '2012-04-08 10:52:42.0',
    'completeddatetime': '2012-04-08 10:56:50.902884',
    'cpu_info': 'None | 0',
    'cpu_name': 'arm',
    'crashedThread': 8,
    'date_processed': '2012-04-08 10:56:41.558922',
    'distributor': None,
    'distributor_version': None,
    'dump': '...',
    'email': 'bogus@bogus.com',
    'flash_version': '[blank]',
    'hangid': None,
    'id': 361399767,
    'json_dump': {
        'things': 'stackwalker output',
        'largest_free_vm_block': '0x2F42',
        'tiny_block_size': 42,
        'write_combine_size': 43,
        'system_info': {
            'cpu_count': 42,
            'os': 'Linux',
        },
    },
    'install_age': 22385,
    'last_crash': None,
    'memory_report': {
        'version': 1,
        'reports': [],
    },
    'os_name': 'Linux',
    'os_version': '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ',
    'processor_notes': 'SignatureTool: signature truncated due to length',
    'process_type': 'plugin',
    'product': 'FennecAndroid',
    'PluginFilename': 'dwight.txt',
    'PluginName': 'wilma',
    'PluginVersion': '69',
    'reason': 'SIGSEGV',
    'release_channel': 'default',
    'ReleaseChannel': 'default',
    'signature': 'libxul.so@0x117441c',
    'started_datetime': '2012-04-08 10:56:50.440752',
    'startedDateTime': '2012-04-08 10:56:50.440752',
    'success': True,
    'topmost_filenames': [],
    'truncated': False,
    'uptime': 170,
    'url': 'http://embarasing.porn.com',
    'user_comments': None,
    'user_id': None,
    'uuid': '936ce666-ff3b-4c7a-9674-367fe2120408',
    'version': '13.0a1',
    'upload_file_minidump_flash1': {
        'things': 'untouched',
        'json_dump': 'stackwalker output',
    },
    'upload_file_minidump_flash2': {
        'things': 'untouched',
        'json_dump': 'stackwalker output',
    },
    'upload_file_minidump_browser': {
        'things': 'untouched',
        'json_dump': 'stackwalker output',
    },
}

a_processed_crash_with_no_stackwalker = deepcopy(a_processed_crash)

a_processed_crash_with_no_stackwalker['date_processed'] = \
    string_to_datetime('2012-04-08 10:56:41.558922')
a_processed_crash_with_no_stackwalker['client_crash_date'] =  \
    string_to_datetime('2012-04-08 10:52:42.0')
a_processed_crash_with_no_stackwalker['completeddatetime'] =  \
    string_to_datetime('2012-04-08 10:56:50.902884')
a_processed_crash_with_no_stackwalker['started_datetime'] =  \
    string_to_datetime('2012-04-08 10:56:50.440752')
a_processed_crash_with_no_stackwalker['startedDateTime'] =  \
    string_to_datetime('2012-04-08 10:56:50.440752')

del a_processed_crash_with_no_stackwalker['json_dump']
del a_processed_crash_with_no_stackwalker['upload_file_minidump_flash1'][
    'json_dump'
]
del a_processed_crash_with_no_stackwalker['upload_file_minidump_flash2'][
    'json_dump'
]
del a_processed_crash_with_no_stackwalker['upload_file_minidump_browser'][
    'json_dump'
]

a_raw_crash = {
    'foo': 'alpha',
    'bar': 42
}


class TestRawCrashRedactor(TestCaseWithConfig):
    """Test the custom RawCrashRedactor class does indeed redact crashes.
    """

    def __init__(self, *args, **kwargs):
        super(TestRawCrashRedactor, self).__init__(*args, **kwargs)
        self.config = self.get_tuned_config(RawCrashRedactor)

    def test_redact_raw_crash(self):
        redactor = RawCrashRedactor(self.config)
        crash = {
            'Key1': 'value',
            'Key2': [12, 23, 34],
            'StackTraces': 'foo:bar',
            'Key3': {
                'a': 1,
            },
        }
        expected_crash = {
            'Key1': 'value',
            'Key2': [12, 23, 34],
            'Key3': {
                'a': 1,
            },
        }

        redactor.redact(crash)
        eq_(crash, expected_crash)


class IntegrationTestESCrashStorage(ElasticsearchTestCase):
    """These tests interact with Elasticsearch (or some other external
    resource).
    """

    def __init__(self, *args, **kwargs):
        super(IntegrationTestESCrashStorage, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(ESCrashStorage)

        # Helpers for interacting with ES outside of the context of a
        # specific test.
        self.es_client = elasticsearch.Elasticsearch(
            hosts=self.config.elasticsearch.elasticsearch_urls
        )
        self.index_client = elasticsearch.client.IndicesClient(self.es_client)

    def setUp(self):
        """Set up the default index to satisfy eventual test dependencies.
        """

        super(IntegrationTestESCrashStorage, self).setUp()

    def tearDown(self):
        """Remove indices that may have been created by the test.
        """
        try:
            self.index_client.delete(
                self.config.elasticsearch.elasticsearch_index
            )

        except elasticsearch.exceptions.NotFoundError:
            # It's fine it's fine; 404 means the test didn't create any
            # indices, therefore they can't be deleted.
            pass

    def test_index_crash(self):
        """Test indexing a crash document.
        """

        es_storage = ESCrashStorage(config=self.config)

        es_storage.save_raw_and_processed(
            raw_crash=a_raw_crash,
            dumps=None,
            processed_crash=a_processed_crash,
            crash_id=a_processed_crash['uuid']
        )

        # Ensure that the document was indexed by attempting to retreive it.
        ok_(
            self.es_client.get(
                index=self.config.elasticsearch.elasticsearch_index,
                id=a_processed_crash['uuid']
            )
        )
        es_storage.close()

    def test_bulk_index_crash(self):
        """Test indexing a crash document.
        """

        local_config = self.get_tuned_config(
            ESBulkCrashStorage,
            {"items_per_bulk_load": 10, }
        )

        es_storage = ESBulkCrashStorage(config=local_config)

        for x in range(20):
            uuid = "%02d%s" % (
                x,
                a_processed_crash['uuid'][2:]
            )
            new_processed_crash = deepcopy(a_processed_crash)
            new_processed_crash['uuid'] = uuid

            es_storage.save_raw_and_processed(
                raw_crash=a_raw_crash,
                dumps=None,
                processed_crash=new_processed_crash,
                crash_id=uuid
            )
        es_storage.close()

        for x in range(20):
            uuid = "%02d%s" % (
                x,
                a_processed_crash['uuid'][2:]
            )
            # Ensure that the document was indexed by attempting to retreive it
            ok_(
                self.es_client.get(
                    index=local_config.elasticsearch.elasticsearch_index,
                    id=uuid
                )
            )


class TestESCrashStorage(ElasticsearchTestCase):
    """These tests are self-contained and use Mock where necessary.
    """

    def __init__(self, *args, **kwargs):
        super(TestESCrashStorage, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(ESCrashStorage)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_index_for_crash_static_name(self):
        """Test a static index name.
        """

        es_storage = ESCrashStorage(config=self.config)

        # The actual date isn't important since the index name won't use it.
        index = es_storage.get_index_for_crash('some_date')

        # The index name is obtained from the test base class.
        ok_(type(index) is str)
        eq_(index, 'socorro_integration_test_reports')

    def test_get_index_for_crash_dynamic_name(self):
        """Test a dynamic (date-based) index name.
        """

        # The crashstorage class looks for '%' in the index name; if that
        # symbol is present, it will attempt to generate a new date-based
        # index name. Since the test base config doesn't use this pattern,
        # we need to specify it now.
        modified_config = self.get_tuned_config(
            ESCrashStorage,
            {'resource.elasticsearch.elasticsearch_index':
                'socorro_integration_test_reports%Y%m%d'}
        )
        es_storage = ESCrashStorage(config=modified_config)

        # The date is used to generate the name of the index; it must be a
        # datetime object.
        date = string_to_datetime(
            a_processed_crash['client_crash_date']
        )
        index = es_storage.get_index_for_crash(date)

        # The base index name is obtained from the test base class and the
        # date is appended to it according to pattern specified above.
        ok_(type(index) is str)
        eq_(index, 'socorro_integration_test_reports20120408')

    def test_index_crash(self):
        """Mock test the entire crash submission mechanism.
        """

        es_storage = ESCrashStorage(config=self.config)

        # This is the function that would actually connect to ES; by mocking
        # it entirely we are ensuring that ES doesn't actually get touched.
        es_storage._submit_crash_to_elasticsearch = mock.Mock()

        es_storage.save_raw_and_processed(
            raw_crash=a_raw_crash,
            dumps=None,
            processed_crash=a_processed_crash,
            crash_id=a_processed_crash['uuid']
        )

        # Ensure that the indexing function is only called once.
        eq_(es_storage._submit_crash_to_elasticsearch.call_count, 1)

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_success(self, espy_mock):
        """Test a successful index of a crash report.
        """

        # It's mocks all the way down.
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash['uuid']

        # Submit a crash like normal, except that the back-end ES object is
        # mocked (see the decorator above).
        es_storage.save_raw_and_processed(
            raw_crash=a_raw_crash,
            dumps=None,
            processed_crash=a_processed_crash,
            crash_id=crash_id,
        )

        # Ensure that the ES objects were instantiated by ConnectionContext.
        ok_(espy_mock.Elasticsearch.called)

        # Ensure that the IndicesClient was also instantiated (this happens in
        # IndexCreator but is part of the crashstorage workflow).
        ok_(espy_mock.client.IndicesClient.called)

        # The actual call to index the document (crash).
        document = {
            'crash_id': crash_id,
            'processed_crash': a_processed_crash,
            'raw_crash': a_raw_crash
        }

        additional = {
            'doc_type': 'crash_reports',
            'id': crash_id,
            'index': 'socorro_integration_test_reports'
        }

        sub_mock.index.assert_called_with(
            body=document,
            **additional
        )

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_success_with_no_stackwalker_class(self, espy_mock):
        """Test a successful index of a crash report.
        """
        modified_config = deepcopy(self.config)
        modified_config.es_redactor = DotDict()
        modified_config.es_redactor.redactor_class = Redactor
        modified_config.es_redactor.forbidden_keys = (
            "json_dump, "
            "upload_file_minidump_flash1.json_dump, "
            "upload_file_minidump_flash2.json_dump, "
            "upload_file_minidump_browser.json_dump"
        )
        modified_config.raw_crash_es_redactor = DotDict()
        modified_config.raw_crash_es_redactor.redactor_class = RawCrashRedactor
        modified_config.raw_crash_es_redactor.forbidden_keys = 'unsused'

        # It's mocks all the way down.
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorageRedactedSave(config=modified_config)

        crash_id = a_processed_crash['uuid']

        # Submit a crash like normal, except that the back-end ES object is
        # mocked (see the decorator above).
        es_storage.save_raw_and_processed(
            raw_crash=a_raw_crash,
            dumps=None,
            processed_crash=a_processed_crash,
            crash_id=crash_id,
        )

        # Ensure that the ES objects were instantiated by ConnectionContext.
        ok_(espy_mock.Elasticsearch.called)

        # Ensure that the IndicesClient was also instantiated (this happens in
        # IndexCreator but is part of the crashstorage workflow).
        ok_(espy_mock.client.IndicesClient.called)

        # The actual call to index the document (crash).
        document = {
            'crash_id': crash_id,
            'processed_crash': a_processed_crash_with_no_stackwalker,
            'raw_crash': a_raw_crash
        }

        additional = {
            'doc_type': 'crash_reports',
            'id': crash_id,
            'index': 'socorro_integration_test_reports'
        }

        sub_mock.index.assert_called_with(
            body=document,
            **additional
        )

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_success_with_limited_json_dump_class(self, espy_mock):
        """Test a successful index of a crash report.
        """
        modified_config = deepcopy(self.config)
        modified_config.json_dump_whitelist_keys = [
            "largest_free_vm_block",
            "tiny_block_size",
            "write_combine_size",
            "system_info",
        ]
        modified_config.es_redactor = DotDict()
        modified_config.es_redactor.redactor_class = Redactor
        modified_config.es_redactor.forbidden_keys = (
            "memory_report, "
            "upload_file_minidump_flash1.json_dump, "
            "upload_file_minidump_flash2.json_dump, "
            "upload_file_minidump_browser.json_dump"
        )
        modified_config.raw_crash_es_redactor = DotDict()
        modified_config.raw_crash_es_redactor.redactor_class = RawCrashRedactor
        modified_config.raw_crash_es_redactor.forbidden_keys = 'unsused'

        # It's mocks all the way down.
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorageRedactedJsonDump(config=modified_config)

        crash_id = a_processed_crash['uuid']

        # Submit a crash like normal, except that the back-end ES object is
        # mocked (see the decorator above).
        es_storage.save_raw_and_processed(
            raw_crash=a_raw_crash,
            dumps=None,
            processed_crash=deepcopy(a_processed_crash),
            crash_id=crash_id,
        )

        # Ensure that the ES objects were instantiated by ConnectionContext.
        ok_(espy_mock.Elasticsearch.called)

        # Ensure that the IndicesClient was also instantiated (this happens in
        # IndexCreator but is part of the crashstorage workflow).
        ok_(espy_mock.client.IndicesClient.called)

        expected_processed_crash = deepcopy(
            a_processed_crash_with_no_stackwalker
        )
        expected_processed_crash['json_dump'] = {
            k: a_processed_crash['json_dump'][k]
            for k in modified_config.json_dump_whitelist_keys
        }
        del expected_processed_crash['memory_report']

        # The actual call to index the document (crash).
        document = {
            'crash_id': crash_id,
            'processed_crash': expected_processed_crash,
            'raw_crash': a_raw_crash
        }

        additional = {
            'doc_type': 'crash_reports',
            'id': crash_id,
            'index': 'socorro_integration_test_reports'
        }

        sub_mock.index.assert_called_with(
            body=document,
            **additional
        )

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_success_with_redacted_raw_crash(self, espy_mock):
        """Test a successful index of a crash report.
        """
        modified_config = deepcopy(self.config)
        modified_config.es_redactor = DotDict()
        modified_config.es_redactor.redactor_class = Redactor
        modified_config.es_redactor.forbidden_keys = 'unsused'
        modified_config.raw_crash_es_redactor = DotDict()
        modified_config.raw_crash_es_redactor.redactor_class = RawCrashRedactor
        modified_config.raw_crash_es_redactor.forbidden_keys = 'unsused'

        # It's mocks all the way down.
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorageRedactedSave(config=modified_config)

        crash_id = a_processed_crash['uuid']

        # Add a 'StackTraces' field to be redacted.
        raw_crash = deepcopy(a_raw_crash)
        raw_crash['StackTraces'] = 'something'

        # Submit a crash like normal, except that the back-end ES object is
        # mocked (see the decorator above).
        es_storage.save_raw_and_processed(
            raw_crash=raw_crash,
            dumps=None,
            processed_crash=deepcopy(a_processed_crash),
            crash_id=crash_id,
        )

        # Ensure that the ES objects were instantiated by ConnectionContext.
        ok_(espy_mock.Elasticsearch.called)

        # Ensure that the IndicesClient was also instantiated (this happens in
        # IndexCreator but is part of the crashstorage workflow).
        ok_(espy_mock.client.IndicesClient.called)

        # The actual call to index the document (crash).
        document = {
            'crash_id': crash_id,
            'processed_crash': a_processed_crash,
            'raw_crash': a_raw_crash  # Note here we expect the original dict
        }

        additional = {
            'doc_type': 'crash_reports',
            'id': crash_id,
            'index': 'socorro_integration_test_reports'
        }

        sub_mock.index.assert_called_with(
            body=document,
            **additional
        )

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_fatal_failure(self, espy_mock):
        """Test an index attempt that fails catastrophically.
        """

        # It's mocks all the way down.
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash['uuid']

        # Oh the humanity!
        failure_exception = Exception('horrors')
        sub_mock.index.side_effect = failure_exception

        # Submit a crash and ensure that it failed.
        assert_raises(
            Exception,
            es_storage.save_raw_and_processed,
            a_raw_crash,
            None,
            a_processed_crash,
            crash_id
        )

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_fatal_operational_exception(self, espy_mock):
        """Test an index attempt that experiences an operational exception that
        it can't recover from.
        """

        # It's mocks all the way down.
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        # ESCrashStorage uses the "limited backoff" transaction executor.
        # In real life this will retry operational exceptions over time, but
        # in unit tests, we just want it to hurry up and fail.
        backoff_config = self.config
        backoff_config['backoff_delays'] = [0, 0, 0]
        backoff_config['wait_log_interval'] = 0

        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash['uuid']

        # It's bad but at least we expected it.
        failure_exception = elasticsearch.exceptions.ConnectionError(500, '')
        sub_mock.index.side_effect = failure_exception

        # Submit a crash and ensure that it failed.
        assert_raises(
            elasticsearch.exceptions.ConnectionError,
            es_storage.save_raw_and_processed,
            a_raw_crash,
            None,
            a_processed_crash,
            crash_id
        )

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_success_operational_exception(self, espy_mock):
        """Test an index attempt that experiences an operational exception that
        it managed to recover from.
        """

        # It's mocks all the way down.
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        # ESCrashStorage uses the "limited backoff" transaction executor.
        # In real life this will retry operational exceptions over time, but
        # in unit tests, we just want it to hurry up and fail.
        backoff_config = self.config
        backoff_config['backoff_delays'] = [0, 0, 0]
        backoff_config['wait_log_interval'] = 0

        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash['uuid']

        # The transaction executor will try three times, so we will fail
        # twice for the purposes of this test.
        bad_results = [
            elasticsearch.exceptions.ConnectionError(500, ''),
            elasticsearch.exceptions.ConnectionError(500, '')
        ]

        # Replace the underlying index method with this function.
        def esindex_fn(*args, **kwargs):
            try:
                result = bad_results.pop(0)
                raise result
            except IndexError:
                return sub_mock.index

        sub_mock.index.side_effect = esindex_fn

        # Submit a crash like normal, except that the index method will
        # raise twice, then pass as normal.
        es_storage.save_raw_and_processed(
            raw_crash=a_raw_crash,
            dumps=None,
            processed_crash=a_processed_crash,
            crash_id=crash_id,
        )

        # The actual call to index the document (crash).
        document = {
            'crash_id': crash_id,
            'processed_crash': a_processed_crash,
            'raw_crash': a_raw_crash
        }

        additional = {
            'doc_type': 'crash_reports',
            'id': crash_id,
            'index': 'socorro_integration_test_reports'
        }

        sub_mock.index.assert_called_with(
            body=document,
            **additional
        )

    @mock.patch('elasticsearch.client')
    @mock.patch('elasticsearch.Elasticsearch')
    def test_indexing_bogus_string_field(self, es_class_mock, es_client_mock):
        """Test an index attempt that fails because of a bogus string field.
        Expected behavior is to remove that field and retry indexing.
        """
        # ESCrashStorage uses the "limited backoff" transaction executor.
        # In real life this will retry operational exceptions over time, but
        # in unit tests, we just want it to hurry up and fail.
        backoff_config = self.config
        backoff_config['backoff_delays'] = [0, 0, 0]
        backoff_config['wait_log_interval'] = 0

        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash['uuid']
        raw_crash = {}
        processed_crash = {
            'date_processed': '2012-04-08 10:56:41.558922',
            'bogus-field': 'some bogus value',
            'foo': 'bar',
        }

        def mock_index(*args, **kwargs):
            if 'bogus-field' in kwargs['body']['processed_crash']:
                raise elasticsearch.exceptions.TransportError(
                    400,
                    'RemoteTransportException[[i-5exxx97][inet[/172.3.9.12:'
                    '9300]][indices:data/write/index]]; nested: '
                    'IllegalArgumentException[Document contains at least one '
                    'immense term in field="processed_crash.bogus-field.full" '
                    '(whose UTF8 encoding is longer than the max length 32766)'
                    ', all of which were skipped.  Please correct the analyzer'
                    ' to not produce such terms.  The prefix of the first '
                    'immense term is: \'[124, 91, 48, 93, 91, 71, 70, 88, 49, '
                    '45, 93, 58, 32, 65, 116, 116, 101, 109, 112, 116, 32, '
                    '116, 111, 32, 99, 114, 101, 97, 116, 101]...\', original '
                    'message: bytes can be at most 32766 in length; got 98489]'
                    '; nested: MaxBytesLengthExceededException'
                    '[bytes can be at most 32766 in length; got 98489]; '
                )

            return True

        es_class_mock().index.side_effect = mock_index

        # Submit a crash and ensure that it succeeds.
        es_storage.save_raw_and_processed(
            raw_crash,
            None,
            processed_crash,
            crash_id
        )

        expected_doc = {
            'crash_id': crash_id,
            'removed_fields': 'processed_crash.bogus-field',
            'processed_crash': {
                'date_processed': string_to_datetime(
                    '2012-04-08 10:56:41.558922'
                ),
                'foo': 'bar',
            },
            'raw_crash': {},
        }
        es_class_mock().index.assert_called_with(
            index=self.config.elasticsearch.elasticsearch_index,
            doc_type=self.config.elasticsearch.elasticsearch_doctype,
            body=expected_doc,
            id=crash_id
        )

    @mock.patch('elasticsearch.client')
    @mock.patch('elasticsearch.Elasticsearch')
    def test_indexing_bogus_number_field(self, es_class_mock, es_client_mock):
        """Test an index attempt that fails because of a bogus number field.
        Expected behavior is to remove that field and retry indexing.
        """
        # ESCrashStorage uses the "limited backoff" transaction executor.
        # In real life this will retry operational exceptions over time, but
        # in unit tests, we just want it to hurry up and fail.
        backoff_config = self.config
        backoff_config['backoff_delays'] = [0, 0, 0]
        backoff_config['wait_log_interval'] = 0

        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash['uuid']
        raw_crash = {}
        processed_crash = {
            'date_processed': '2012-04-08 10:56:41.558922',
            'bogus-field': 1234567890,
            'foo': 'bar',
        }

        def mock_index(*args, **kwargs):
            if 'bogus-field' in kwargs['body']['processed_crash']:
                raise elasticsearch.exceptions.TransportError(
                    400,
                    'RemoteTransportException[[i-f94dae31][inet[/172.31.1.54:'
                    '9300]][indices:data/write/index]]; nested: '
                    'MapperParsingException[failed to parse '
                    '[processed_crash.bogus-field]]; nested: '
                    'NumberFormatException[For input string: '
                    '"18446744073709480735"]; '
                )

            return True

        es_class_mock().index.side_effect = mock_index

        # Submit a crash and ensure that it succeeds.
        es_storage.save_raw_and_processed(
            raw_crash,
            None,
            processed_crash,
            crash_id
        )

        expected_doc = {
            'crash_id': crash_id,
            'removed_fields': 'processed_crash.bogus-field',
            'processed_crash': {
                'date_processed': string_to_datetime(
                    '2012-04-08 10:56:41.558922'
                ),
                'foo': 'bar',
            },
            'raw_crash': {},
        }
        es_class_mock().index.assert_called_with(
            index=self.config.elasticsearch.elasticsearch_index,
            doc_type=self.config.elasticsearch.elasticsearch_doctype,
            body=expected_doc,
            id=crash_id
        )

    @mock.patch('elasticsearch.client')
    @mock.patch('elasticsearch.Elasticsearch')
    def test_indexing_unhandled_errors(self, es_class_mock, es_client_mock):
        """Test an index attempt that fails because of unhandled errors.
        Expected behavior is to fail indexing and raise the error.
        """
        # ESCrashStorage uses the "limited backoff" transaction executor.
        # In real life this will retry operational exceptions over time, but
        # in unit tests, we just want it to hurry up and fail.
        backoff_config = self.config
        backoff_config['backoff_delays'] = [0, 0, 0]
        backoff_config['wait_log_interval'] = 0

        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash['uuid']
        raw_crash = {}
        processed_crash = {
            'date_processed': '2012-04-08 10:56:41.558922',
        }

        # Test with an error from which a field name cannot be extracted.
        def mock_index_unparsable_error(*args, **kwargs):
            raise elasticsearch.exceptions.TransportError(
                400,
                'RemoteTransportException[[i-f94dae31][inet[/172.31.1.54:'
                '9300]][indices:data/write/index]]; nested: '
                'MapperParsingException[BROKEN PART]; NumberFormatException'
            )

            return True

        es_class_mock().index.side_effect = mock_index_unparsable_error

        assert_raises(
            elasticsearch.exceptions.TransportError,
            es_storage.save_raw_and_processed,
            raw_crash,
            None,
            processed_crash,
            crash_id
        )

        # Test with an error that we do not handle.
        def mock_index_unhandled_error(*args, **kwargs):
            raise elasticsearch.exceptions.TransportError(
                400,
                'Something went wrong'
            )

            return True

        es_class_mock().index.side_effect = mock_index_unhandled_error

        assert_raises(
            elasticsearch.exceptions.TransportError,
            es_storage.save_raw_and_processed,
            raw_crash,
            None,
            processed_crash,
            crash_id
        )

    def test_crash_size_capture(self):
        """Verify we capture raw/processed crash sizes in ES crashstorage"""
        es_storage = ESCrashStorage(config=self.config)

        es_storage._submit_crash_to_elasticsearch = mock.Mock()

        es_storage.save_raw_and_processed(
            raw_crash=a_raw_crash,
            dumps=None,
            processed_crash=a_processed_crash,
            crash_id=a_processed_crash['uuid']
        )

        mock_calls = [str(call) for call in self.config.metrics.mock_calls]
        # NOTE(willkg): The sizes of these json documents depend on what's in them. If we changed
        # a_processed_crash and a_raw_crash, then these numbers will change.
        assert 'call.histogram(\'processor.es.raw_crash_size\', 27)' in mock_calls
        assert 'call.histogram(\'processor.es.processed_crash_size\', 1785)' in mock_calls
