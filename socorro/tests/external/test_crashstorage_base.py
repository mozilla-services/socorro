# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    MemoryDumpsMapping,
)


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
            crashstorage.delete_crash(crash_id)

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
