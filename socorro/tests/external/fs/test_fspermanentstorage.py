# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os

import pytest

from socorro.external.crashstorage_base import CrashIDNotFound, MemoryDumpsMapping
from socorro.external.fs.crashstorage import FSPermanentStorage


class TestFSPermanentStorage:
    def test_save_raw_crash(self, tmp_path):
        fs = FSPermanentStorage(fs_root=str(tmp_path))

        crash_id = "0bba929f-8721-460c-dead-a43c20071025"
        raw_crash = {"ProductName": "Firefox"}
        fs.save_raw_crash(raw_crash=raw_crash, dumps={}, crash_id=crash_id)

        assert os.path.exists(fs._get_radixed_parent_directory(crash_id))

    def test_save_processed_crash(self, tmp_path):
        fs = FSPermanentStorage(fs_root=str(tmp_path))

        crash_id = "0bba929f-8721-460c-dead-a43c20071025"
        raw_crash = {"ProductName": "Firefox"}
        processed_crash = {"uuid": crash_id, "product_name": "Firefox"}
        fs.save_processed_crash(raw_crash=raw_crash, processed_crash=processed_crash)

        assert os.path.exists(
            os.path.join(
                fs._get_radixed_parent_directory(crash_id),
                crash_id + fs.jsonz_file_suffix,
            )
        )

    def test_get_raw_crash(self, tmp_path):
        fs = FSPermanentStorage(fs_root=str(tmp_path))

        crash_id = "0bba929f-8721-460c-dead-a43c20071025"
        raw_crash = {"ProductName": "Firefox"}

        with pytest.raises(CrashIDNotFound):
            fs.get_raw_crash(crash_id)

        fs.save_raw_crash(raw_crash=raw_crash, dumps={}, crash_id=crash_id)
        ret = fs.get_raw_crash(crash_id)
        assert ret["ProductName"] == "Firefox"

    def test_get_processed_crash(self, tmp_path):
        fs = FSPermanentStorage(fs_root=str(tmp_path))

        crash_id = "0bba929f-8721-460c-dead-a43c20071025"
        raw_crash = {"ProductName": "Firefox"}
        processed_crash = {"uuid": crash_id, "product_name": "Firefox"}

        with pytest.raises(CrashIDNotFound):
            fs.get_processed_crash(crash_id)

        fs.save_processed_crash(raw_crash=raw_crash, processed_crash=processed_crash)
        ret = fs.get_processed_crash(crash_id)
        assert ret["product_name"] == "Firefox"

    def test_get_raw_dump(self, tmp_path):
        fs = FSPermanentStorage(fs_root=str(tmp_path))

        crash_id = "0bba929f-8721-460c-dead-a43c20071025"
        raw_crash = {"ProductName": "Firefox"}

        with pytest.raises(CrashIDNotFound):
            fs.get_raw_dump(crash_id, name="memory_report")
        with pytest.raises(CrashIDNotFound):
            fs.get_raw_dump(crash_id, name=fs.dump_field)

        dumps = {"memory_report": b"12345", fs.dump_field: b"abcde"}
        fs.save_raw_crash(raw_crash=raw_crash, dumps=dumps, crash_id=crash_id)

        ret = fs.get_raw_dump(crash_id, name="memory_report")
        assert ret == b"12345"

        ret = fs.get_raw_dump(crash_id, name=fs.dump_field)
        assert ret == b"abcde"

    def test_get_dumps(self, tmp_path):
        fs = FSPermanentStorage(fs_root=str(tmp_path))

        crash_id = "0bba929f-8721-460c-dead-a43c20071025"
        raw_crash = {"ProductName": "Firefox"}
        dumps = {"memory_report": b"12345", fs.dump_field: b"abcde"}

        with pytest.raises(CrashIDNotFound):
            fs.get_dumps(crash_id)

        fs.save_raw_crash(raw_crash=raw_crash, dumps=dumps, crash_id=crash_id)
        expected = MemoryDumpsMapping(dumps)
        assert fs.get_dumps(crash_id) == expected

    def test_delete_crash(self, tmp_path):
        fs = FSPermanentStorage(fs_root=str(tmp_path))

        crash_id = "0bba929f-8721-460c-dead-a43c20071025"
        raw_crash = {"ProductName": "Firefox"}
        processed_crash = {"uuid": crash_id, "product_name": "Firefox"}
        dumps = {"memory_report": b"12345", fs.dump_field: b"abcde"}

        fs.save_raw_crash(raw_crash=raw_crash, dumps=dumps, crash_id=crash_id)
        fs.save_processed_crash(raw_crash=raw_crash, processed_crash=processed_crash)

        # Make sure they're all gettable
        fs.get_raw_crash(crash_id)
        fs.get_processed_crash(crash_id)
        fs.get_dumps(crash_id)

        # Remove the data
        fs.delete_crash(crash_id)
        assert not os.path.exists(fs._get_radixed_parent_directory(crash_id))
        with pytest.raises(CrashIDNotFound):
            fs.get_raw_crash(crash_id)
