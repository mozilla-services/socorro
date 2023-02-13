# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from copy import deepcopy
from datetime import timedelta
from unittest import mock

from markus.testing import MetricsMock
import pytest

from socorro.external.es.crashstorage import (
    ESCrashStorage,
    fix_boolean,
    fix_integer,
    fix_keyword,
    fix_long,
    fix_string,
    is_valid_key,
)
from socorro.lib.libdatetime import date_to_string, utc_now, string_to_datetime
from socorro.external.es.super_search_fields import build_mapping
from socorro.tests.external.es.base import ElasticsearchTestCase


# A sample crash report that is used for testing.
SAMPLE_PROCESSED_CRASH = {
    "addons": [["{1a5dabbd-0e74-41da-b532-a364bb552cab}", "1.0.4.1"]],
    "addons_checked": None,
    "address": "0x1c",
    "app_notes": "...",
    "build": "20120309050057",
    "client_crash_date": "2012-04-08 10:52:42.0",
    "completed_datetime": "2012-04-08 10:56:50.902884",
    "cpu_info": "None | 0",
    "cpu_arch": "arm",
    "date_processed": "2012-04-08 10:56:41.558922",
    "hangid": None,
    "id": 361399767,
    "json_dump": {
        "things": "stackwalker output",
        "system_info": {"cpu_count": 42, "os": "Linux"},
    },
    "install_age": 22385,
    "last_crash": None,
    "memory_report": {"version": 1, "reports": []},
    "os_name": "Linux",
    "os_version": "0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ",
    "processor_notes": "SignatureTool: signature truncated due to length",
    "process_type": "plugin",
    "product": "Firefox",
    "PluginFilename": "dwight.txt",
    "PluginName": "wilma",
    "PluginVersion": "69",
    "reason": "SIGSEGV",
    "release_channel": "default",
    "ReleaseChannel": "default",
    "signature": "libxul.so@0x117441c",
    "started_datetime": "2012-04-08 10:56:50.440752",
    "success": True,
    "topmost_filenames": [],
    "uptime": 170,
    "url": "http://embarasing.example.com",
    "user_comments": None,
    "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
    "version": "13.0a1",
    "upload_file_minidump_browser": {
        "things": "untouched",
        "json_dump": "stackwalker output",
    },
}

SAMPLE_RAW_CRASH = {"ProductName": "Firefox", "ReleaseChannel": "nightly"}


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

    def setup_method(self):
        super().setup_method()
        self.config = self.get_tuned_config(ESCrashStorage)

    def test_index_crash(self):
        """Test indexing a crash document."""
        es_storage = ESCrashStorage(config=self.config)

        raw_crash = deepcopy(SAMPLE_RAW_CRASH)
        processed_crash = deepcopy(SAMPLE_PROCESSED_CRASH)
        processed_crash["date_processed"] = date_to_string(utc_now())

        es_storage.save_processed_crash(
            raw_crash=raw_crash,
            processed_crash=processed_crash,
        )

        # Ensure that the document was indexed by attempting to retreive it.
        assert self.conn.get(
            index=self.es_context.get_index_for_date(utc_now()),
            id=SAMPLE_PROCESSED_CRASH["uuid"],
        )
        es_storage.close()

    def test_index_crash_indexable_keys(self):
        # Check super_search_fields.py for valid keys to update this
        raw_crash = {
            "InvalidKey": "alpha",
        }
        processed_crash = {
            "AnotherInvalidKey": "alpha",
            "date_processed": date_to_string(utc_now()),
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
            "dom_fission_enabled": "1",
        }

        es_storage = ESCrashStorage(config=self.config)

        es_storage.save_processed_crash(
            raw_crash=raw_crash,
            processed_crash=processed_crash,
        )

        # Ensure that the document was indexed by attempting to retreive it.
        doc = self.conn.get(
            index=self.es_context.get_index_for_date(utc_now()),
            id=processed_crash["uuid"],
        )

        # Verify keys that aren't in super_search_fields aren't in the raw or processed
        # crash parts
        raw_crash = doc["_source"]["raw_crash"]
        assert list(sorted(raw_crash.keys())) == []

        processed_crash = doc["_source"]["processed_crash"]
        assert list(sorted(processed_crash.keys())) == [
            "date_processed",
            "dom_fission_enabled",
            "uuid",
        ]

    def test_index_crash_mapping_keys(self):
        """Test indexing a crash that has keys not in the mapping

        Indexing a crash that has keys that aren't in the mapping for the index
        should cause those keys to be removed from the crash.

        """
        # The test harness creates an index for this week and last week. So let's create
        # one for 4 weeks ago.
        now = utc_now()
        four_weeks_ago = now - timedelta(days=28)

        field = "user_comments"

        # We're going to use a mapping from super search fields, bug remove the
        # user_comments field.
        mappings = build_mapping(self.es_context.get_doctype())
        doctype = self.es_context.get_doctype()
        del mappings[doctype]["properties"]["processed_crash"]["properties"][field]

        # Create the index for 4 weeks ago
        self.es_context.create_index(
            index_name=self.es_context.get_index_for_date(four_weeks_ago),
            mappings=mappings,
        )

        es_storage = ESCrashStorage(config=self.config)

        # Create a crash for this week and save it
        now_uuid = "00000000-0000-0000-0000-000000120408"
        raw_crash = {
            "BuildID": "20200506000000",
        }
        processed_crash = {
            field: "this week",
            "date_processed": date_to_string(now),
            "uuid": now_uuid,
        }

        es_storage.save_processed_crash(
            raw_crash=raw_crash,
            processed_crash=processed_crash,
        )

        # Create a crash for four weeks ago with the bum mapping and save it
        old_uuid = "11111111-1111-1111-1111-111111120408"
        raw_crash = {
            "BuildID": "20200506000000",
        }
        processed_crash = {
            field: "this week",
            "date_processed": date_to_string(now - timedelta(days=28)),
            "uuid": old_uuid,
        }

        es_storage.save_processed_crash(
            raw_crash=raw_crash,
            processed_crash=processed_crash,
        )

        self.es_context.refresh()

        # Retrieve the document from this week and verify it has the user_comments
        # field
        doc = self.conn.get(
            index=self.es_context.get_index_for_date(now),
            id=now_uuid,
        )
        assert field in doc["_source"]["processed_crash"]

        # Retrieve the document from four weeks ago and verify it doesn't have the
        # user_comments field
        doc = self.conn.get(
            index=self.es_context.get_index_for_date(four_weeks_ago),
            id=old_uuid,
        )
        assert field not in doc["_source"]["processed_crash"]


class TestESCrashStorage(ElasticsearchTestCase):
    """These tests are self-contained and use Mock where necessary"""

    def setup_method(self):
        super().setup_method()
        self.config = self.get_tuned_config(ESCrashStorage)

    def test_index_crash(self):
        """Mock test the entire crash submission mechanism"""
        es_storage = ESCrashStorage(config=self.config)

        # This is the function that would actually connect to ES; by mocking
        # it entirely we are ensuring that ES doesn't actually get touched.
        es_storage._submit_crash_to_elasticsearch = mock.Mock()

        es_storage.save_processed_crash(
            raw_crash=deepcopy(SAMPLE_RAW_CRASH),
            processed_crash=deepcopy(SAMPLE_PROCESSED_CRASH),
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
            "date_processed": date_to_string(utc_now()),
            "dom_fission_enabled": "1",
        }

        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        crash_id = processed_crash["uuid"]

        # Submit a crash like normal, except that the back-end ES object is
        # mocked (see the decorator above).
        es_storage = ESCrashStorage(config=self.config)
        es_storage.save_processed_crash(
            raw_crash=raw_crash,
            processed_crash=processed_crash,
        )

        # Ensure that the ES objects were instantiated by ConnectionContext.
        assert espy_mock.Elasticsearch.called

        # Ensure that the IndicesClient was also instantiated (this happens in
        # IndexCreator but is part of the crashstorage workflow).
        assert espy_mock.client.IndicesClient.called

        # The actual call to index the document (crash).
        document = {
            "crash_id": crash_id,
            "raw_crash": {},
            "processed_crash": {
                "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
                "date_processed": string_to_datetime(processed_crash["date_processed"]),
                "dom_fission_enabled": "1",
            },
        }

        additional = {
            "doc_type": "crash_reports",
            "id": crash_id,
            "index": self.es_context.get_index_for_date(utc_now()),
        }

        sub_mock.index.assert_called_with(body=document, **additional)

    @mock.patch("socorro.external.es.connection_context.elasticsearch")
    def test_fatal_failure(self, espy_mock):
        """Test an index attempt that fails catastrophically"""
        sub_mock = mock.MagicMock()
        espy_mock.Elasticsearch.return_value = sub_mock

        es_storage = ESCrashStorage(config=self.config)

        crash_id = SAMPLE_PROCESSED_CRASH["uuid"]

        # Oh the humanity!
        failure_exception = Exception("horrors")
        sub_mock.index.side_effect = failure_exception

        # Submit a crash and ensure that it failed.
        with pytest.raises(Exception):
            es_storage.save_processed_crash(
                raw_crash=deepcopy(SAMPLE_RAW_CRASH),
                dumps=None,
                processed_crsah=deepcopy(SAMPLE_PROCESSED_CRASH),
                crash_id=crash_id,
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
                raw_crash=raw_crash,
                processed_crash=processed_crash,
            )

            mm.assert_histogram("processor.es.raw_crash_size", value=2)
            mm.assert_histogram("processor.es.processed_crash_size", value=96)
            mm.assert_histogram("processor.es.crash_document_size", value=186)

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


@pytest.mark.parametrize(
    "value, expected",
    [
        # Non-string values are converted to "BAD DATA"
        (1, "BAD DATA"),
        # String values are truncated if > 10,000 characters
        ("a" * 9_999, "a" * 9_999),
        ("a" * 10_000, "a" * 10_000),
        ("a" * 10_001, "a" * 10_000),
    ],
)
def test_fix_keyword(value, expected):
    new_value = fix_keyword(value, max_size=10_000)
    assert new_value == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        # Non string values are converted to "BAD DATA"
        (1, "BAD DATA"),
        # String values are truncated if > 32,766 characters
        ("a" * 32_765, "a" * 32_765),
        ("a" * 32_766, "a" * 32_766),
        ("a" * 32_767, "a" * 32_766),
        # Bad Unicode values shouldn't throw an exception
        (
            b"hi \xc3there".decode("utf-8", "surrogateescape"),
            "BAD DATA",
        ),
    ],
)
def test_fix_string(value, expected):
    new_value = fix_string(value, max_size=32_766)
    assert new_value == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        # True-ish values are True
        (True, True),
        ("true", True),
        (1, True),
        ("1", True),
        # Everything else is False
        (None, False),
        (0, False),
        ("0", False),
        ("false", False),
        ("somethingrandom", False),
        (False, False),
    ],
)
def test_convert_booleans_values(value, expected):
    new_value = fix_boolean(value)
    assert new_value == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        # Field is valid
        (0, 0),
        # Field is a string and valid, gets converted to int
        ("0", 0),
        # Field is out of bounds, gets removed
        (-2_147_483_650, None),
        (2_147_483_650, None),
    ],
)
def test_fix_integer(value, expected):
    # Note: data is modified in place
    new_value = fix_integer(value)
    assert new_value == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        # Field is valid
        (0, 0),
        # Field is a string and valid, gets converted to int
        ("0", 0),
        # Field is out of bounds, gets removed
        (-9_223_372_036_854_775_810, None),
        (9_223_372_036_854_775_810, None),
    ],
)
def test_fix_long(value, expected):
    new_value = fix_long(value)
    assert new_value == expected
