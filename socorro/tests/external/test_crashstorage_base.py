# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    MemoryDumpsMapping,
    migrate_raw_crash,
)


class Test_migrate_raw_crash:
    @pytest.mark.parametrize(
        "data, expected",
        [
            # Empty dict turns into defaults
            (
                {},
                {
                    "metadata": {
                        "collector_notes": [],
                        "dump_checksums": {},
                        "migrated_from_version_1": True,
                        "payload_compressed": "0",
                        "payload": "unknown",
                    },
                    "version": 2,
                },
            ),
            # If it's version 2 already, nothing happens
            (
                {
                    "metadata": {
                        "collector_notes": [],
                        "dump_checksums": {},
                        "payload_compressed": "0",
                        "payload": "json",
                    },
                    "version": 2,
                },
                {
                    "metadata": {
                        "collector_notes": [],
                        "dump_checksums": {},
                        "payload_compressed": "0",
                        "payload": "json",
                    },
                    "version": 2,
                },
            ),
            # Migrate version 1 to latest
            (
                {
                    "BuildID": "20220902183841",
                    "CrashTime": "1662147837",
                    "ProductName": "Firefox",
                    "collector_notes": ["note1"],
                    "dump_checksums": {"upload_file_minidump": "hash"},
                    "payload": "json",
                    "payload_compressed": "0",
                    "submitted_timestamp": "2022-09-02T19:44:32.762212+00:00",
                    "uuid": "20aec939-4154-4520-ba3c-024930220902",
                },
                {
                    "BuildID": "20220902183841",
                    "CrashTime": "1662147837",
                    "ProductName": "Firefox",
                    "metadata": {
                        "collector_notes": ["note1"],
                        "dump_checksums": {"upload_file_minidump": "hash"},
                        "migrated_from_version_1": True,
                        "payload_compressed": "0",
                        "payload": "json",
                    },
                    "submitted_timestamp": "2022-09-02T19:44:32.762212+00:00",
                    "uuid": "20aec939-4154-4520-ba3c-024930220902",
                    "version": 2,
                },
            ),
        ],
    )
    def test_migration(self, data, expected):
        assert migrate_raw_crash(data) == expected


class TestCrashStorageBase:
    def test_not_implemented(self):
        crashstorage = CrashStorageBase()

        crash_id = "0bba929f-8721-460c-dead-a43c20071025"

        crashstorage.save_raw_crash(raw_crash={}, dumps={}, crash_id=crash_id)
        with pytest.raises(NotImplementedError):
            crashstorage.get_raw_crash(crash_id)

        with pytest.raises(NotImplementedError):
            crashstorage.get_raw_dump(crash_id, name="upload_file_minidump")

        with pytest.raises(NotImplementedError):
            crashstorage.get_processed_crash(crash_id)

        with pytest.raises(NotImplementedError):
            crashstorage.remove(crash_id)

        crashstorage.close()


class TestDumpsMappings:
    def test_simple(self):
        mdm = MemoryDumpsMapping(
            {"upload_file_minidump": b"binary_data", "moar_dump": b"more binary data"}
        )
        assert mdm.as_memory_dumps_mapping() is mdm
        fdm = mdm.as_file_dumps_mapping("a", "/tmp", "dump")
        assert fdm.as_file_dumps_mapping() is fdm
        assert fdm.as_memory_dumps_mapping() == mdm
