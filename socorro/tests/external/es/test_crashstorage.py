# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from copy import deepcopy
from datetime import timedelta
from unittest import mock

import glom
from markus.testing import AnyTagValue, MetricsMock
import pytest

from socorro import settings
from socorro.external.es.crashstorage import (
    fix_boolean,
    fix_integer,
    fix_keyword,
    fix_long,
    fix_string,
    fix_float,
)

from socorro.external.es.super_search_fields import build_mapping
from socorro.libclass import build_instance_from_settings
from socorro.lib.libdatetime import date_to_string, string_to_datetime, utc_now
from socorro.lib.libooid import create_new_ooid, date_from_ooid


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

REMOVED_VALUE = object()


class FakeException(Exception):
    pass


class TestESCrashStorage:
    def build_crashstorage(self):
        if settings.ELASTICSEARCH_MODE == "LEGACY_ONLY":
            raise ValueError("cannot test elasticearch 8 in LEGACY_ONLY mode")

        return build_instance_from_settings(settings.ES_STORAGE)

    def test_index_crash(self, es_helper):
        """Test indexing a crash document."""
        processed_crash = deepcopy(SAMPLE_PROCESSED_CRASH)
        processed_crash["date_processed"] = date_to_string(utc_now())

        crashstorage = self.build_crashstorage()
        crashstorage.save_processed_crash(
            raw_crash={},
            processed_crash=processed_crash,
        )

        with es_helper.conn() as conn:
            assert conn.get(
                index=crashstorage.get_index_for_date(utc_now()),
                id=SAMPLE_PROCESSED_CRASH["uuid"],
            )

    def test_index_crash_indexable_keys(self, es_helper):
        """Test indexing ONLY indexes valid, known keys."""
        processed_crash = {
            "another_invalid_key": "alpha",
            "date_processed": date_to_string(utc_now()),
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
            "dom_fission_enabled": "1",
        }

        crashstorage = self.build_crashstorage()
        crashstorage.save_processed_crash(
            raw_crash={},
            processed_crash=processed_crash,
        )

        with es_helper.conn() as conn:
            doc = conn.get(
                index=crashstorage.get_index_for_date(utc_now()),
                id=processed_crash["uuid"],
            )

        # Verify keys that aren't in super_search_fields aren't in the the final
        # document
        processed_crash = doc["_source"]["processed_crash"]
        assert list(sorted(processed_crash.keys())) == [
            "date_processed",
            "dom_fission_enabled",
            "uuid",
        ]

    def test_index_crash_mapping_keys(self, es_helper):
        """Test indexing a crash that has keys not in the mapping

        Indexing a crash that has keys that aren't in the mapping for the index
        should cause those keys to be removed from the crash.

        """
        # Delete all the indices so we have a fresh start
        es_helper.delete_indices()

        # The test harness creates an index for this week and last week. So let's create
        # one for 4 weeks ago.
        now = utc_now()
        four_weeks_ago = now - timedelta(days=28)

        field = "user_comments"

        crashstorage = self.build_crashstorage()

        # We're going to use a mapping from super search fields, bug remove the
        # user_comments field.
        mappings = build_mapping()
        del mappings["properties"]["processed_crash"]["properties"][field]

        # Create the index for 4 weeks ago
        crashstorage.create_index(
            index_name=crashstorage.get_index_for_date(four_weeks_ago),
            mappings=mappings,
        )

        # Create a crash for this week and save it
        now_uuid = create_new_ooid(timestamp=now)
        processed_crash = {
            field: "this week",
            "date_processed": date_to_string(now),
            "uuid": now_uuid,
        }

        crashstorage.save_processed_crash(
            raw_crash={},
            processed_crash=processed_crash,
        )

        # Create a crash for four weeks ago with the bum mapping and save it
        old_uuid = create_new_ooid(timestamp=four_weeks_ago)
        processed_crash = {
            field: "this week",
            "date_processed": date_to_string(now - timedelta(days=28)),
            "uuid": old_uuid,
        }

        crashstorage.save_processed_crash(
            raw_crash={},
            processed_crash=processed_crash,
        )

        es_helper.refresh()

        # Retrieve the document from this week and verify it has the user_comments
        # field
        with es_helper.conn() as conn:
            doc = conn.get(
                index=crashstorage.get_index_for_date(now),
                id=now_uuid,
            )
            assert field in doc["_source"]["processed_crash"]

        # Retrieve the document from four weeks ago and verify it doesn't have the
        # user_comments field
        with es_helper.conn() as conn:
            doc = conn.get(
                index=crashstorage.get_index_for_date(four_weeks_ago),
                id=old_uuid,
            )
            assert field not in doc["_source"]["processed_crash"]

    def test_catalog_crash(self, es_helper):
        crash_id = create_new_ooid()
        processed_crash = deepcopy(SAMPLE_PROCESSED_CRASH)
        processed_crash["date_processed"] = date_to_string(utc_now())
        processed_crash["uuid"] = crash_id

        crashstorage = self.build_crashstorage()
        crashstorage.save_processed_crash(
            raw_crash={},
            processed_crash=processed_crash,
        )
        es_helper.refresh()

        data = crashstorage.catalog_crash(crash_id=crash_id)
        assert data == ["es_processed_crash"]

    def test_delete_crash(self, es_helper):
        """Test deleting a crash document."""
        crash_id = create_new_ooid()
        processed_crash = deepcopy(SAMPLE_PROCESSED_CRASH)
        processed_crash["date_processed"] = date_to_string(utc_now())
        processed_crash["uuid"] = crash_id

        crashstorage = self.build_crashstorage()
        crashstorage.save_processed_crash(
            raw_crash={},
            processed_crash=processed_crash,
        )
        es_helper.refresh()

        # Verify the crash is in the index
        data = es_helper.get_crash_data(crash_id=crash_id)
        assert data is not None

        # Delete the crash and refresh cluster
        crashstorage.delete_crash(crash_id=crash_id)

        # Verify crash data is gone
        data = es_helper.get_crash_data(crash_id=crash_id)
        assert data is None

    def test_delete_crash_doesnt_exist(self, es_helper):
        """Test deleting a crash document."""
        crash_id = create_new_ooid()

        crashstorage = self.build_crashstorage()
        crashstorage.delete_crash(crash_id=crash_id)

    def test_crash_size_capture(self):
        """Verify saving a processed crash emits a metric for crash document size"""
        crash_id = create_new_ooid()
        processed_crash = {
            "date_processed": "2012-04-08 10:56:41.558922",
            "uuid": crash_id,
        }

        crashstorage = self.build_crashstorage()
        with MetricsMock() as mm:
            crashstorage.save_processed_crash(
                raw_crash={},
                processed_crash=processed_crash,
            )

            mm.assert_histogram("socorro.processor.es.crash_document_size", value=169)

    def test_index_data_capture(self, es_helper):
        """Verify we capture index data in ES crashstorage"""
        crashstorage = self.build_crashstorage()
        mock_connection = mock.Mock()
        with MetricsMock() as mm:
            # Successful indexing
            crashstorage._index_crash(
                connection=mock_connection,
                es_index=None,
                crash_document=None,
                crash_id=None,
            )
            # Failed indexing
            mock_connection.index.side_effect = FakeException
            with pytest.raises(FakeException):
                crashstorage._index_crash(
                    connection=mock_connection,
                    es_index=None,
                    crash_document=None,
                    crash_id=None,
                )

            mm.assert_histogram_once(
                "socorro.processor.es.index",
                tags=["outcome:successful", AnyTagValue("host")],
            )
            mm.assert_histogram_once(
                "socorro.processor.es.index",
                tags=["outcome:failed", AnyTagValue("host")],
            )

    def test_delete_expired_indices(self, es_helper):
        # Delete any existing indices first
        es_helper.delete_indices()
        es_helper.refresh()
        es_helper.health_check()

        # Create an index > retention_policy
        crashstorage = self.build_crashstorage()
        template = crashstorage.get_index_template()
        now = utc_now()
        current_index_name = now.strftime(template)
        before_retention_policy = now - timedelta(weeks=crashstorage.retention_policy)
        old_index_name = before_retention_policy.strftime(template)

        crashstorage.create_index(current_index_name)
        crashstorage.create_index(old_index_name)
        es_helper.health_check()
        assert list(es_helper.get_indices()) == [old_index_name, current_index_name]

        # Delete all expired indices and verify old one is gone and new one is still
        # there
        crashstorage.delete_expired_indices()
        es_helper.health_check()
        assert list(es_helper.get_indices()) == [current_index_name]

    # NOTE(willkg): This is dependent on supersearch fields. As we adjust
    # supersearch fields, we may need to update this test.
    @pytest.mark.parametrize(
        "key, value, expected_value",
        [
            # Non-string keyword converted to "BAD DATA"
            ("processed_crash.background_task_name", 44, "BAD DATA"),
            # Long keywords are truncated
            pytest.param(
                "processed_crash.background_task_name",
                "a" * 10_001,
                "a" * 10_000,
                id="long_keywords_truncated",
            ),
            # Non-string string converted to "BAD DATA"
            ("processed_crash.user_comments", 44, "BAD DATA"),
            # Long strings are truncated
            pytest.param(
                "processed_crash.user_comments",
                "a" * 32_767,
                "a" * 32_766,
                id="long_strings_truncated",
            ),
            # Out-of-bounds integers are removed
            (
                "processed_crash.mac_available_memory_sysctl",
                2_147_483_999,
                REMOVED_VALUE,
            ),
            # Out-of-bounds longs are removed
            (
                "processed_crash.memory_explicit",
                9_223_372_036_854_775_999,
                REMOVED_VALUE,
            ),
            # Booleans are converted
            ("processed_crash.accessibility", "true", True),
        ],
    )
    def test_indexing_bad_data(self, key, value, expected_value, es_helper):
        crash_id = create_new_ooid()
        processed_crash = {
            "date_processed": date_from_ooid(crash_id),
            "uuid": crash_id,
        }

        # Put the processed_crash in a doc like we index so the keys match the shape of
        # the structure, then set the value, then extract the processed crash structure
        # so we can save it
        doc = {"processed_crash": processed_crash}
        glom.assign(doc, key, value, missing=dict)
        processed_crash = doc["processed_crash"]

        # Save the crash data and then fetch it and verify the value is as expected
        crashstorage = self.build_crashstorage()
        crashstorage.save_processed_crash(
            raw_crash={},
            processed_crash=processed_crash,
        )
        es_helper.refresh()

        doc = es_helper.get_crash_data(crash_id)
        assert glom.glom(doc, key, default=REMOVED_VALUE) == expected_value

    @pytest.mark.parametrize(
        "key, value",
        [
            pytest.param(
                "processed_crash.mac_available_memory_sysctl",
                "not a number",
                id="number_format_exception",
            ),
            pytest.param(
                "processed_crash.user_comments",
                "a" * 32_767,  # max string lengthis 32_766 bytes
                id="max_bytes_length_exceeded",
            ),
            pytest.param(
                "processed_crash.user_comments", {"foo": "bar"}, id="unknown_property"
            ),
        ],
    )
    def test_invalid_fields_removed(self, key, value, es_helper):
        # create crash document
        crash_id = create_new_ooid()
        doc = {
            "crash_id": crash_id,
            "processed_crash": {
                "date_processed": date_from_ooid(crash_id),
                "uuid": crash_id,
            },
        }
        glom.assign(doc, key, value, missing=dict)

        # Save the crash data and then fetch it and verify the value is removed
        crashstorage = self.build_crashstorage()
        index_name = crashstorage.get_index_for_date(
            string_to_datetime(doc["processed_crash"]["date_processed"])
        )
        crashstorage._submit_crash_to_elasticsearch(
            crash_id=crash_id,
            index_name=index_name,
            crash_document=doc,
        )
        es_helper.refresh()

        doc = es_helper.get_crash_data(crash_id)
        assert glom.glom(doc, key, default=REMOVED_VALUE) == REMOVED_VALUE


@pytest.mark.parametrize(
    "value, expected",
    [
        # Non-string values are converted to "BAD DATA"
        (1, "BAD DATA"),
        # Keyword string values are truncated if > 10,000 characters
        pytest.param("a" * 9_999, "a" * 9_999, id="keyword_9_999"),
        pytest.param("a" * 10_000, "a" * 10_000, id="keyword_10_000"),
        pytest.param("a" * 10_001, "a" * 10_000, id="keyword_10_001_truncated"),
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
        pytest.param("a" * 32_765, "a" * 32_765, id="string_32_765"),
        pytest.param("a" * 32_766, "a" * 32_766, id="string_32_766"),
        pytest.param("a" * 32_767, "a" * 32_766, id="string_32_767_truncated"),
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


@pytest.mark.parametrize(
    "value, expected",
    [
        # Field is valid
        (0, 0),
        # Field is a string and valid, gets converted to int
        ("0", 0),
        # Field is out of bounds, gets removed
        (float("-inf"), None),
        (float("inf"), None),
        (float("nan"), None),
    ],
)
def test_fix_float(value, expected):
    new_value = fix_float(value)
    assert new_value == expected
