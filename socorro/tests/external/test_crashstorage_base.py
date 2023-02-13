# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from configman import Namespace, ConfigurationManager
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


class A(CrashStorageBase):
    foo = "a"
    required_config = Namespace()
    required_config.add_option("x", default=1)
    required_config.add_option("y", default=2)

    def __init__(self, config, namespace=""):
        super().__init__(config, namespace)
        self.raw_crash_count = 0

    def save_raw_crash(self, raw_crash, dump):
        pass

    def save_processed_crash(self, processed_crash):
        pass


class B(A):
    foo = "b"
    required_config = Namespace()
    required_config.add_option("z", default=2)


class TestCrashStorageBase:
    def test_basic_crashstorage(self):
        required_config = Namespace()

        mock_logging = mock.Mock()
        required_config.add_option("logger", default=mock_logging)
        required_config.update(CrashStorageBase.required_config)

        config_manager = ConfigurationManager(
            [required_config],
            app_name="testapp",
            app_version="1.0",
            app_description="app description",
            values_source_list=[{"logger": mock_logging}],
            argv_source=[],
        )

        with config_manager.context() as config:
            crashstorage = CrashStorageBase(config)
            crashstorage.save_raw_crash({}, "payload", "ooid")
            with pytest.raises(NotImplementedError):
                crashstorage.get_raw_crash("ooid")

            with pytest.raises(NotImplementedError):
                crashstorage.get_raw_dump("ooid")

            with pytest.raises(NotImplementedError):
                crashstorage.get_processed("ooid")

            with pytest.raises(NotImplementedError):
                crashstorage.remove("ooid")

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
