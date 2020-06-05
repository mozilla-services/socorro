# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from copy import deepcopy
from unittest import mock

from configman.dotdict import DotDict
import elasticsearch
from markus.testing import MetricsMock
import pytest

from socorro.external.crashstorage_base import Redactor
from socorro.external.es.crashstorage import (
    convert_booleans,
    ESCrashStorage,
    ESCrashStorageRedactedSave,
    ESCrashStorageRedactedJsonDump,
    get_fields_by_analyzer,
    is_valid_key,
    RawCrashRedactor,
    reconstitute_datetimes,
    truncate_keyword_field_values,
    truncate_string_field_values,
)
from socorro.lib.datetimeutil import string_to_datetime
from socorro.lib.ooid import create_new_ooid
from socorro.unittest.external.es.base import ElasticsearchTestCase, TestCaseWithConfig


# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)


# A dummy crash report that is used for testing.
a_processed_crash = {
    "addons": [["{1a5dabbd-0e74-41da-b532-a364bb552cab}", "1.0.4.1"]],
    "addons_checked": None,
    "address": "0x1c",
    "app_notes": "...",
    "build": "20120309050057",
    "client_crash_date": "2012-04-08 10:52:42.0",
    "completeddatetime": "2012-04-08 10:56:50.902884",
    "cpu_info": "None | 0",
    "cpu_arch": "arm",
    "crashedThread": 8,
    "date_processed": "2012-04-08 10:56:41.558922",
    "email": "bogus@bogus.com",
    "flash_version": "[blank]",
    "hangid": None,
    "id": 361399767,
    "json_dump": {
        "things": "stackwalker output",
        "largest_free_vm_block": "0x2F42",
        "tiny_block_size": 42,
        "write_combine_size": 43,
        "system_info": {"cpu_count": 42, "os": "Linux"},
    },
    "install_age": 22385,
    "last_crash": None,
    "memory_report": {"version": 1, "reports": []},
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
    "started_datetime": "2012-04-08 10:56:50.440752",
    "startedDateTime": "2012-04-08 10:56:50.440752",
    "success": True,
    "topmost_filenames": [],
    "truncated": False,
    "uptime": 170,
    "url": "http://embarasing.example.com",
    "user_comments": None,
    "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
    "version": "13.0a1",
    "upload_file_minidump_flash1": {
        "things": "untouched",
        "json_dump": "stackwalker output",
    },
    "upload_file_minidump_flash2": {
        "things": "untouched",
        "json_dump": "stackwalker output",
    },
    "upload_file_minidump_browser": {
        "things": "untouched",
        "json_dump": "stackwalker output",
    },
}

a_raw_crash = {"ProductName": "Firefox", "ReleaseChannel": "nightly"}


class TestRawCrashRedactor(TestCaseWithConfig):
    """Test the custom RawCrashRedactor class does indeed redact crashes"""

    def test_redact_raw_crash(self):
        redactor = RawCrashRedactor(self.get_tuned_config(RawCrashRedactor))
        crash = {
            "Key1": "value",
            "Key2": [12, 23, 34],
            "StackTraces": "foo:bar",
            "Key3": {"a": 1},
        }
        expected_crash = {"Key1": "value", "Key2": [12, 23, 34], "Key3": {"a": 1}}

        redactor.redact(crash)
        assert crash == expected_crash


class TestIsValidKey:
    @pytest.mark.parametrize(
        "key", ["a", "abc", "ABC", "AbcDef", "Abc_Def", "Abc-def" "Abc-123-def"]
    )
    def test_valid_key(self, key):
        assert is_valid_key(key) is True

    @pytest.mark.parametrize("key", ["", ".", "abc def", "na\xefve"])
    def test_invalid_key(self, key):
        assert is_valid_key(key) is False


class TestIntegrationESCrashStorage(ElasticsearchTestCase):
    """These tests interact with Elasticsearch (or some other external resource)."""

    def setup_method(self, method):
        super().setup_method(method)
        self.config = self.get_tuned_config(ESCrashStorage)

        # Helpers for interacting with ES outside of the context of a
        # specific test.
        self.es_client = elasticsearch.Elasticsearch(
            hosts=self.config.elasticsearch.elasticsearch_urls
        )
        self.index_client = elasticsearch.client.IndicesClient(self.es_client)

    def test_index_crash(self):
        """Test indexing a crash document."""
        es_storage = ESCrashStorage(config=self.config)

        es_storage.save_processed_crash(
            raw_crash=deepcopy(a_raw_crash),
            processed_crash=deepcopy(a_processed_crash),
        )

        # Ensure that the document was indexed by attempting to retreive it.
        assert self.es_client.get(
            index=es_storage.es_context.get_index_template(),
            id=a_processed_crash["uuid"],
        )
        es_storage.close()

    def test_index_crash_indexable_keys(self):
        # Check super_search_fields.py for valid keys to update this
        raw_crash = {
            "InvalidKey": "alpha",
            "BuildID": "20200506000000",
        }
        processed_crash = {
            "AnotherInvalidKey": "alpha",
            "date_processed": "2012-04-08 10:56:41.558922",
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
        }

        es_storage = ESCrashStorage(config=self.config)

        es_storage.save_processed_crash(
            raw_crash=raw_crash, processed_crash=processed_crash,
        )

        # Ensure that the document was indexed by attempting to retreive it.
        doc = self.es_client.get(
            index=self.config.elasticsearch.elasticsearch_index,
            id=processed_crash["uuid"],
        )

        # Verify keys that aren't in super_search_fields aren't in the raw or processed
        # crash parts
        raw_crash = doc["_source"]["raw_crash"]
        assert raw_crash == {"BuildID": "20200506000000"}
        processed_crash = doc["_source"]["processed_crash"]
        assert processed_crash == {
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
            "date_processed": "2012-04-08T10:56:41.558922+00:00",
        }


class TestESCrashStorage(ElasticsearchTestCase):
    """These tests are self-contained and use Mock where necessary"""

    def setup_method(self, method):
        super().setup_method(method)
        self.config = self.get_tuned_config(ESCrashStorage)

    def test_get_index_for_crash_static_name(self):
        """Test a static index name """
        es_storage = ESCrashStorage(config=self.config)

        # The actual date isn't important since the index name won't use it.
        index = es_storage.get_index_for_crash("some_date")

        # The index name is obtained from the test base class.
        assert type(index) is str
        assert index == "socorro_integration_test_reports"

    def test_get_index_for_crash_dynamic_name(self):
        """Test a dynamic (date-based) index name """

        # The crashstorage class looks for '%' in the index name; if that
        # symbol is present, it will attempt to generate a new date-based
        # index name. Since the test base config doesn't use this pattern,
        # we need to specify it now.
        modified_config = self.get_tuned_config(
            ESCrashStorage,
            {
                "resource.elasticsearch.elasticsearch_index": "socorro_integration_test_reports%Y%m%d"
            },
        )
        es_storage = ESCrashStorage(config=modified_config)

        # The date is used to generate the name of the index; it must be a
        # datetime object.
        date = string_to_datetime(a_processed_crash["client_crash_date"])
        index = es_storage.get_index_for_crash(date)

        # The base index name is obtained from the test base class and the
        # date is appended to it according to pattern specified above.
        assert type(index) is str
        assert index == "socorro_integration_test_reports20120408"

    def test_index_crash(self):
        """Mock test the entire crash submission mechanism"""
        es_storage = ESCrashStorage(config=self.config)

        # This is the function that would actually connect to ES; by mocking
        # it entirely we are ensuring that ES doesn't actually get touched.
        es_storage._submit_crash_to_elasticsearch = mock.Mock()

        es_storage.save_processed_crash(
            raw_crash=deepcopy(a_raw_crash),
            processed_crash=deepcopy(a_processed_crash),
        )

        # Ensure that the indexing function is only called once.
        assert es_storage._submit_crash_to_elasticsearch.call_count == 1

    @mock.patch("socorro.external.es.connection_context.elasticsearch")
    def test_success(self, espy_mock):
        """Test a successful index of a crash report"""
        raw_crash = {
            "BuildID": "20200605000",
            "ProductName": "Firefox",
            "ReleaseChannel": "nightly",
        }
        processed_crash = {
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
            "json_dump": {},
            "date_processed": "2012-04-08 10:56:41.558922",
        }

        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        crash_id = processed_crash["uuid"]

        # Submit a crash like normal, except that the back-end ES object is
        # mocked (see the decorator above).
        es_storage = ESCrashStorage(config=self.config)
        es_storage.save_processed_crash(
            raw_crash=raw_crash, processed_crash=processed_crash,
        )

        # Ensure that the ES objects were instantiated by ConnectionContext.
        assert espy_mock.Elasticsearch.called

        # Ensure that the IndicesClient was also instantiated (this happens in
        # IndexCreator but is part of the crashstorage workflow).
        assert espy_mock.client.IndicesClient.called

        expected_processed_crash = deepcopy(processed_crash)
        reconstitute_datetimes(expected_processed_crash)

        # The actual call to index the document (crash).
        document = {
            "crash_id": crash_id,
            "processed_crash": expected_processed_crash,
            "raw_crash": raw_crash,
        }

        additional = {
            "doc_type": "crash_reports",
            "id": crash_id,
            "index": "socorro_integration_test_reports",
        }

        sub_mock.index.assert_called_with(body=document, **additional)

    @mock.patch("socorro.external.es.connection_context.elasticsearch")
    def test_success_with_limited_json_dump_class(self, espy_mock):
        """Test a successful index of a crash report"""
        modified_config = self.get_tuned_config(ESCrashStorage)
        modified_config.json_dump_allowlist_keys = [
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
        modified_config.raw_crash_es_redactor.forbidden_keys = "unsused"

        processed_crash = {
            "build": "20120309050057",
            "date_processed": "2012-04-08 10:56:41.558922",
            "product": "FennecAndroid",
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
            "json_dump": {
                # json dump allowed keys
                "largest_free_vm_block": "0x2F42",
                "system_info": {"cpu_count": 42, "os": "Linux"},
                "tiny_block_size": 42,
                "write_combine_size": 43,
                # not allowed keys:
                "badkey1": "foo",
                "badkey2": {"badsubkey": "foo"},
            },
        }

        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorageRedactedJsonDump(config=modified_config)

        crash_id = processed_crash["uuid"]

        # Submit a crash like normal, except that the back-end ES object is
        # mocked (see the decorator above).
        es_storage.save_processed_crash(
            raw_crash=deepcopy(a_raw_crash), processed_crash=processed_crash,
        )

        # Ensure that the ES objects were instantiated by ConnectionContext.
        assert espy_mock.Elasticsearch.called

        # Ensure that the IndicesClient was also instantiated (this happens in
        # IndexCreator but is part of the crashstorage workflow).
        assert espy_mock.client.IndicesClient.called

        expected_processed_crash = deepcopy(processed_crash)
        reconstitute_datetimes(expected_processed_crash)
        expected_processed_crash["json_dump"] = {
            k: a_processed_crash["json_dump"][k]
            for k in modified_config.json_dump_allowlist_keys
        }

        # The actual call to index the document (crash).
        document = {
            "crash_id": crash_id,
            "processed_crash": expected_processed_crash,
            "raw_crash": a_raw_crash,
        }

        additional = {
            "doc_type": "crash_reports",
            "id": crash_id,
            "index": "socorro_integration_test_reports",
        }

        sub_mock.index.assert_called_with(body=document, **additional)

    @mock.patch("socorro.external.es.connection_context.elasticsearch")
    def test_success_with_redacted_raw_crash(self, espy_mock):
        """Test a successful index of a crash report"""
        modified_config = deepcopy(self.config)
        modified_config.es_redactor = DotDict()
        modified_config.es_redactor.redactor_class = Redactor
        modified_config.es_redactor.forbidden_keys = "unsused"
        modified_config.raw_crash_es_redactor = DotDict()
        modified_config.raw_crash_es_redactor.redactor_class = RawCrashRedactor
        modified_config.raw_crash_es_redactor.forbidden_keys = "unsused"

        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorageRedactedSave(config=modified_config)

        raw_crash = {
            "BuildID": "20200605000",
            "ProductName": "Firefox",
            "ReleaseChannel": "nightly",
            # Add a 'StackTraces' field to be redacted.
            "StackTraces": "something",
        }
        processed_crash = {
            "date_processed": "2012-04-08 10:56:41.558922",
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
        }
        crash_id = processed_crash["uuid"]

        # Submit a crash like normal, except that the back-end ES object is
        # mocked (see the decorator above).
        es_storage.save_processed_crash(
            raw_crash=raw_crash, processed_crash=processed_crash,
        )

        # Ensure that the ES objects were instantiated by ConnectionContext.
        assert espy_mock.Elasticsearch.called

        # Ensure that the IndicesClient was also instantiated (this happens in
        # IndexCreator but is part of the crashstorage workflow).
        assert espy_mock.client.IndicesClient.called

        expected_raw_crash = deepcopy(raw_crash)
        del expected_raw_crash["StackTraces"]

        expected_processed_crash = deepcopy(processed_crash)
        reconstitute_datetimes(expected_processed_crash)

        # The actual call to index the document (crash).
        document = {
            "crash_id": crash_id,
            "processed_crash": expected_processed_crash,
            "raw_crash": expected_raw_crash,
        }

        additional = {
            "doc_type": "crash_reports",
            "id": crash_id,
            "index": "socorro_integration_test_reports",
        }

        sub_mock.index.assert_called_with(body=document, **additional)

    @mock.patch("socorro.external.es.connection_context.elasticsearch")
    def test_fatal_failure(self, espy_mock):
        """Test an index attempt that fails catastrophically"""
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash["uuid"]

        # Oh the humanity!
        failure_exception = Exception("horrors")
        sub_mock.index.side_effect = failure_exception

        # Submit a crash and ensure that it failed.
        with pytest.raises(Exception):
            es_storage.save_processed_crash(
                raw_crash=deepcopy(a_raw_crash),
                dumps=None,
                processed_crsah=deepcopy(a_processed_crash),
                crash_id=crash_id,
            )

    @mock.patch("elasticsearch.client")
    @mock.patch("elasticsearch.Elasticsearch")
    def test_indexing_bogus_string_field(self, es_class_mock, es_client_mock):
        """Test an index attempt that fails because of a bogus string field.

        Expected behavior is to remove that field and retry indexing.

        """
        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash["uuid"]
        raw_crash = {}
        processed_crash = {
            "date_processed": "2012-04-08 10:56:41.558922",
            # NOTE(willkg): This needs to be a key that's in super_search_fields, but is
            # rejected by our mock_index call--this is wildly contrived.
            "version": "some bogus value",
            "uuid": crash_id,
        }

        def mock_index(*args, **kwargs):
            if "version" in kwargs["body"]["processed_crash"]:
                raise elasticsearch.exceptions.TransportError(
                    400,
                    "RemoteTransportException[[i-5exxx97][inet[/172.3.9.12:"
                    "9300]][indices:data/write/index]]; nested: "
                    "IllegalArgumentException[Document contains at least one "
                    'immense term in field="processed_crash.version.full" '
                    "(whose UTF8 encoding is longer than the max length 32766)"
                    ", all of which were skipped.  Please correct the analyzer"
                    " to not produce such terms.  The prefix of the first "
                    "immense term is: '[124, 91, 48, 93, 91, 71, 70, 88, 49, "
                    "45, 93, 58, 32, 65, 116, 116, 101, 109, 112, 116, 32, "
                    "116, 111, 32, 99, 114, 101, 97, 116, 101]...', original "
                    "message: bytes can be at most 32766 in length; got 98489]"
                    "; nested: MaxBytesLengthExceededException"
                    "[bytes can be at most 32766 in length; got 98489]; ",
                )

            return True

        es_class_mock().index.side_effect = mock_index

        # Submit a crash and ensure that it succeeds.
        es_storage.save_processed_crash(
            raw_crash=deepcopy(raw_crash), processed_crash=deepcopy(processed_crash),
        )

        expected_doc = {
            "crash_id": crash_id,
            "removed_fields": "processed_crash.version",
            "processed_crash": {
                "date_processed": string_to_datetime("2012-04-08 10:56:41.558922"),
                "uuid": crash_id,
            },
            "raw_crash": {},
        }
        es_class_mock().index.assert_called_with(
            index=self.config.elasticsearch.elasticsearch_index,
            doc_type=self.config.elasticsearch.elasticsearch_doctype,
            body=expected_doc,
            id=crash_id,
        )

    @mock.patch("elasticsearch.client")
    @mock.patch("elasticsearch.Elasticsearch")
    def test_indexing_bogus_number_field(self, es_class_mock, es_client_mock):
        """Test an index attempt that fails because of a bogus number field.

        Expected behavior is to remove that field and retry indexing.

        """
        es_storage = ESCrashStorage(config=self.config)

        crash_id = a_processed_crash["uuid"]
        raw_crash = {}
        processed_crash = {
            "date_processed": "2012-04-08 10:56:41.558922",
            # NOTE(willkg): This needs to be a key that's in super_search_fields, but is
            # rejected by our mock_index call--this is wildly contrived.
            "version": 1234567890,
            "uuid": crash_id,
        }

        def mock_index(*args, **kwargs):
            if "version" in kwargs["body"]["processed_crash"]:
                raise elasticsearch.exceptions.TransportError(
                    400,
                    (
                        "RemoteTransportException[[i-f94dae31][inet[/172.31.1.54:"
                        "9300]][indices:data/write/index]]; nested: "
                        "MapperParsingException[failed to parse "
                        "[processed_crash.version]]; nested: "
                        "NumberFormatException[For input string: "
                        '"18446744073709480735"]; '
                    ),
                )

            return True

        es_class_mock().index.side_effect = mock_index

        # Submit a crash and ensure that it succeeds.
        es_storage.save_processed_crash(
            raw_crash=deepcopy(raw_crash), processed_crash=deepcopy(processed_crash),
        )

        expected_doc = {
            "crash_id": crash_id,
            "removed_fields": "processed_crash.version",
            "processed_crash": {
                "date_processed": string_to_datetime("2012-04-08 10:56:41.558922"),
                "uuid": crash_id,
            },
            "raw_crash": {},
        }
        es_class_mock().index.assert_called_with(
            index=self.config.elasticsearch.elasticsearch_index,
            doc_type=self.config.elasticsearch.elasticsearch_doctype,
            body=expected_doc,
            id=crash_id,
        )

    @mock.patch("elasticsearch.client")
    @mock.patch("elasticsearch.Elasticsearch")
    def test_indexing_unknown_property_field(self, es_class_mock, es_client_mock):
        """Test an index attempt that fails because of an unknown property.

        Expected behavior is to remove that field and retry indexing.

        """
        es_storage = ESCrashStorage(config=self.config)

        crash_id = create_new_ooid()
        raw_crash = {
            "ProductName": "Firefox",
        }
        processed_crash = {
            "date_processed": "2019-12-11 10:56:41.558922",
            # NOTE(willkg): This needs to be a key that's in super_search_fields, but is
            # rejected by our mock_index call--this is wildly contrived.
            "version": {"key": {"nested_key": "val"}},
            "uuid": crash_id,
        }

        def mock_index(*args, **kwargs):
            if "version" in kwargs["body"]["processed_crash"]:
                raise elasticsearch.exceptions.TransportError(
                    400,
                    (
                        "RemoteTransportException[[Madam Slay]"
                        "[inet[/172.31.22.181:9300]][indices:data/write/index]]; "
                        "nested: MapperParsingException"
                        "[failed to parse [processed_crash.version]]; "
                        "nested: "
                        "ElasticsearchIllegalArgumentException[unknown property [key]]"
                    ),
                )

            return True

        es_class_mock().index.side_effect = mock_index

        # Submit crash and verify.
        es_storage.save_processed_crash(
            raw_crash=raw_crash, processed_crash=processed_crash,
        )

        expected_doc = {
            "crash_id": crash_id,
            "removed_fields": "processed_crash.version",
            "processed_crash": {
                "date_processed": string_to_datetime("2019-12-11 10:56:41.558922"),
                "uuid": crash_id,
            },
            "raw_crash": raw_crash,
        }
        es_class_mock().index.assert_called_with(
            index=self.config.elasticsearch.elasticsearch_index,
            doc_type=self.config.elasticsearch.elasticsearch_doctype,
            body=expected_doc,
            id=crash_id,
        )

    @mock.patch("elasticsearch.client")
    @mock.patch("elasticsearch.Elasticsearch")
    def test_indexing_unhandled_errors(self, es_class_mock, es_client_mock):
        """Test an index attempt that fails because of unhandled errors.

        Expected behavior is to fail indexing and raise the error.

        """
        es_storage = ESCrashStorage(config=self.config)

        raw_crash = {}
        processed_crash = {
            "uuid": "9d8e7127-9d98-4d92-8ab1-065982200317",
            "date_processed": "2012-04-08 10:56:41.558922",
        }

        # Test with an error from which a field name cannot be extracted.
        def mock_index_unparsable_error(*args, **kwargs):
            raise elasticsearch.exceptions.TransportError(
                400,
                "RemoteTransportException[[i-f94dae31][inet[/172.31.1.54:"
                "9300]][indices:data/write/index]]; nested: "
                "MapperParsingException[BROKEN PART]; NumberFormatException",
            )

            return True

        es_class_mock().index.side_effect = mock_index_unparsable_error

        with pytest.raises(elasticsearch.exceptions.TransportError):
            es_storage.save_processed_crash(
                raw_crash=deepcopy(raw_crash),
                processed_crash=deepcopy(processed_crash),
            )

        # Test with an error that we do not handle.
        def mock_index_unhandled_error(*args, **kwargs):
            raise elasticsearch.exceptions.TransportError(400, "Something went wrong")

            return True

        es_class_mock().index.side_effect = mock_index_unhandled_error

        with pytest.raises(elasticsearch.exceptions.TransportError):
            es_storage.save_processed_crash(
                raw_crash=deepcopy(raw_crash),
                processed_crash=deepcopy(processed_crash),
            )

    def test_crash_size_capture(self):
        """Verify we capture raw/processed crash sizes in ES crashstorage"""
        raw_crash = {"ProductName": "Firefox", "ReleaseChannel": "nightly"}
        processed_crash = {
            "date_processed": "2012-04-08 10:56:41.558922",
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
        }

        with MetricsMock() as mm:
            es_storage = ESCrashStorage(config=self.config, namespace="processor.es")

            es_storage._submit_crash_to_elasticsearch = mock.Mock()

            es_storage.save_processed_crash(
                raw_crash=raw_crash, processed_crash=processed_crash,
            )

            mm.assert_histogram("processor.es.raw_crash_size", value=55)
            mm.assert_histogram("processor.es.processed_crash_size", value=96)

    def test_index_data_capture(self):
        """Verify we capture index data in ES crashstorage"""
        with MetricsMock() as mm:
            es_storage = ESCrashStorage(config=self.config, namespace="processor.es")

            mock_connection = mock.Mock()
            # Do a successful indexing
            es_storage._index_crash(
                connection=mock_connection,
                es_index=None,
                es_doctype=None,
                crash_document=None,
                crash_id=None,
            )
            # Do a failed indexing
            mock_connection.index.side_effect = Exception
            with pytest.raises(Exception):
                es_storage._index_crash(
                    connection=mock_connection,
                    es_index=None,
                    es_doctype=None,
                    crash_document=None,
                    crash_id=None,
                )

            mm.assert_histogram_once("processor.es.index", tags=["outcome:successful"])
            mm.assert_histogram_once("processor.es.index", tags=["outcome:failed"])


class Test_get_fields_by_analyzer:
    @pytest.mark.parametrize(
        "fields",
        [
            # No fields
            {},
            # No storage_mapping
            {"key": {"in_database_name": "key"}},
            # Wrong or missing analyzer
            {"key": {"in_database_name": "key", "storage_mapping": {"type": "string"}}},
            {
                "key": {
                    "in_database_name": "key",
                    "storage_mapping": {
                        "analyzer": "semicolon_keywords",
                        "type": "string",
                    },
                }
            },
        ],
    )
    def test_no_match(self, fields):
        assert get_fields_by_analyzer(fields, "keyword") == []

    def test_match(self):
        fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "keyword", "type": "string"},
            }
        }
        assert get_fields_by_analyzer(fields, "keyword") == [fields["key"]]

    def test_caching(self):
        # Verify caching works
        fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "keyword", "type": "string"},
            }
        }
        result = get_fields_by_analyzer(fields, "keyword")
        second_result = get_fields_by_analyzer(fields, "keyword")
        assert id(result) == id(second_result)

        # This is the same data as fields, but a different dict, so it has a
        # different id and we won't get the cached version
        second_fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "keyword", "type": "string"},
            }
        }
        third_result = get_fields_by_analyzer(second_fields, "keyword")
        assert id(result) != id(third_result)


class Test_truncate_keyword_field_values:
    @pytest.mark.parametrize(
        "data, expected",
        [
            # Top-level, non-str values are left alone
            ({"key": None}, {"key": None}),
            ({"key": 1}, {"key": 1}),
            # Second-level values are left alone
            ({"key": {"key": "a" * 10_001}}, {"key": {"key": "a" * 10_001}}),
            # Top-level, str values are truncated if > 10,000 characters
            ({"key": "a" * 9_999}, {"key": "a" * 9_999}),
            ({"key": "a" * 10_000}, {"key": "a" * 10_000}),
            ({"key": "a" * 10_001}, {"key": "a" * 10_000}),
        ],
    )
    def test_truncate_keyword_field_values(self, data, expected):
        fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "keyword", "type": "string"},
            }
        }

        # Note: data is modified in place
        truncate_keyword_field_values(fields, data)
        assert data == expected

    @pytest.mark.parametrize(
        "fields",
        [
            # No in_database_name leaves data unchanged
            {"key": {"storage_mapping": {"analyzer": "keyword", "type": "string"}}},
            # Wrong in_database_name leaves data unchanged
            {
                "key": {
                    "in_database_name": "different_key",
                    "storage_mapping": {"analyzer": "keyword", "type": "string"},
                }
            },
        ],
    )
    def test_fields_handling(self, fields):
        """Verify truncation only occurs if all requirements are true

        This also verifies that access of FIELDS handles edge cases like
        missing data.

        """
        original_data = {"key": "a" * 10_001}
        data = deepcopy(original_data)

        truncate_keyword_field_values(fields, data)
        assert original_data == data


class Test_truncate_string_field_values:
    @pytest.mark.parametrize(
        "data, expected",
        [
            # Top-level, non-str values are left alone
            ({"key": None}, {"key": None}),
            ({"key": 1}, {"key": 1}),
            # Second-level values are left alone
            ({"key": {"key": "a" * 32_767}}, {"key": {"key": "a" * 32_767}}),
            # Top-level, str values are truncated if > 32,766 characters
            ({"key": "a" * 32_765}, {"key": "a" * 32_765}),
            ({"key": "a" * 32_766}, {"key": "a" * 32_766}),
            ({"key": "a" * 32_767}, {"key": "a" * 32_766}),
            # Bad Unicode values shouldn't throw an exception
            (
                {"key": b"hi \xc3there".decode("utf-8", "surrogateescape")},
                {"key": "BAD DATA"},
            ),
        ],
    )
    def test_truncate_string_field_values(self, data, expected):
        fields = {
            "key": {"in_database_name": "key", "storage_mapping": {"type": "string"}}
        }

        # Note: data is modified in place
        truncate_string_field_values(fields, data)
        assert data == expected

    @pytest.mark.parametrize(
        "fields",
        [
            # No in_database_name leaves data unchanged
            {"key": {"storage_mapping": {"type": "string"}}},
            # Wrong in_database_name leaves data unchanged
            {
                "key": {
                    "in_database_name": "different_key",
                    "storage_mapping": {"type": "string"},
                }
            },
        ],
    )
    def test_fields_handling(self, fields):
        """Verify truncation only occurs if all requirements are true

        This also verifies that access of FIELDS handles edge cases like
        missing data.

        """
        original_data = {"key": "a" * 32_767}
        data = deepcopy(original_data)

        truncate_string_field_values(fields, data)
        assert original_data == data


class Test_convert_booleans:
    @pytest.mark.parametrize(
        "data, expected",
        [
            # True-ish values are True
            ({"key": True}, {"key": True}),
            ({"key": "true"}, {"key": True}),
            ({"key": 1}, {"key": True}),
            ({"key": "1"}, {"key": True}),
            # Everything else is False
            ({"key": None}, {"key": False}),
            ({"key": 0}, {"key": False}),
            ({"key": "0"}, {"key": False}),
            ({"key": "false"}, {"key": False}),
            ({"key": "somethingrandom"}, {"key": False}),
            ({"key": False}, {"key": False}),
        ],
    )
    def test_convert_booleans_values(self, data, expected):
        fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "boolean"},
            }
        }
        # Note: data is modified in place
        convert_booleans(fields, data)
        assert data == expected

    @pytest.mark.parametrize(
        "fields",
        [
            # No in_database_name leaves data unchanged
            {"key": {"storage_mapping": {"analyzer": "keyword", "type": "string"}}},
            # Wrong in_database_name leaves data unchanged
            {
                "key": {
                    "in_database_name": "different_key",
                    "storage_mapping": {"analyzer": "keyword", "type": "string"},
                }
            },
        ],
    )
    def test_fields_handling(self, fields):
        original_data = {"key": "a" * 10001}
        data = deepcopy(original_data)

        convert_booleans(fields, data)
        assert original_data == data
