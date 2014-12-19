# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import elasticsearch

from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises

from socorro.external import BadArgumentError
from socorro.external.es.crashstorage import ESCrashStorage
from socorro.external.es.connection_context import ConnectionContext
from socorro.unittest.external.es.base import ElasticsearchTestCase
from socorro.lib import datetimeutil


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
    'install_age': 22385,
    'last_crash': None,
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
}

a_raw_crash = {
    'foo': 'alpha',
    'bar': 42
}


# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
#import logging
#logging.getLogger('elasticsearch').setLevel(logging.ERROR)


@attr(integration='elasticsearch') # for nosetests
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

        self.index_super_search_fields()

    def tearDown(self):
        """Remove indices that may have been created by the test.
        """

        try:
            self.index_client.delete(
                self.config.elasticsearch.elasticsearch_default_index
            )

        except elasticsearch.exceptions.NotFoundError:
            # It's fine it's fine; 404 means the test didn't create any
            # indices, therefore they can't be deleted.
            pass


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
            {'resource.elasticsearch.elasticsearch_index': \
                'socorro_integration_test_reports%Y%m%d'}
        )
        es_storage = ESCrashStorage(config=modified_config)

        # The date is used to generate the name of the index; it must be a
        # datetime object.
        date = datetimeutil.string_to_datetime(
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

    #-------------------------------------------------------------------------
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
        """Test an index attempt that experiences a operational exception that
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
        failure_exception = elasticsearch.exceptions.ConnectionError
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
        """Test an index attempt that experiences a operational exception that
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
            elasticsearch.exceptions.ConnectionError,
            elasticsearch.exceptions.ConnectionError
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
