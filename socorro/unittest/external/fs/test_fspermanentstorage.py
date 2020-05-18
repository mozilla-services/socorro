# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil
from unittest import mock

from configman import ConfigurationManager
import pytest

from socorro.external.crashstorage_base import CrashIDNotFound, MemoryDumpsMapping
from socorro.external.fs.crashstorage import FSPermanentStorage


FS_ROOT = os.environ["resource.fs.fs_root"]


class TestFSPermanentStorage:
    CRASH_ID_1 = "0bba929f-8721-460c-dead-a43c20071025"
    CRASH_ID_2 = "0bba929f-8721-460c-dead-a43c20071026"
    CRASH_ID_3 = "0bba929f-8721-460c-dead-a43c20071027"

    def setup_method(self, method):
        with self._common_config_setup().context() as config:
            self.fsrts = FSPermanentStorage(config)

    def teardown_method(self, method):
        shutil.rmtree(self.fsrts.config.fs_root)

    def _common_config_setup(self):
        mock_logging = mock.Mock()
        required_config = FSPermanentStorage.get_required_config()
        required_config.add_option("logger", default=mock_logging)
        config_manager = ConfigurationManager(
            [required_config],
            app_name="testapp",
            app_version="1.0",
            app_description="app description",
            values_source_list=[{"logger": mock_logging, "fs_root": FS_ROOT}],
            argv_source=[],
        )
        return config_manager

    def _make_test_crash(self, crash_id=CRASH_ID_1):
        self.fsrts.save_raw_crash(
            raw_crash={"test": "TEST"},
            dumps=MemoryDumpsMapping(
                {"foo": b"bar", self.fsrts.config.dump_field: b"baz"}
            ),
            crash_id=crash_id,
        )

    def _make_processed_test_crash(self):
        self.fsrts.save_processed_crash(
            {}, {"uuid": self.CRASH_ID_2, "test": "TEST", "email": "should not exist"}
        )

    def test_save_raw_crash(self):
        self._make_test_crash()
        assert os.path.exists(self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1))

    def test_save_processed_crash(self):
        self._make_processed_test_crash()
        assert os.path.exists(
            os.path.join(
                self.fsrts._get_radixed_parent_directory(self.CRASH_ID_2),
                self.CRASH_ID_2 + self.fsrts.config.jsonz_file_suffix,
            )
        )

    def test_get_raw_crash(self):
        self._make_test_crash()
        assert self.fsrts.get_raw_crash(self.CRASH_ID_1)["test"] == "TEST"
        with pytest.raises(CrashIDNotFound):
            self.fsrts.get_raw_crash(self.CRASH_ID_2)

    def test_get_unredacted_processed_crash(self):
        self._make_processed_test_crash()
        assert self.fsrts.get_unredacted_processed(self.CRASH_ID_2)["test"] == "TEST"
        assert "email" in self.fsrts.get_unredacted_processed(self.CRASH_ID_2)
        with pytest.raises(CrashIDNotFound):
            self.fsrts.get_unredacted_processed(self.CRASH_ID_1)

    def test_get_processed_crash(self):
        self._make_processed_test_crash()
        assert self.fsrts.get_processed(self.CRASH_ID_2)["test"] == "TEST"
        assert "email" not in self.fsrts.get_processed(self.CRASH_ID_2)
        with pytest.raises(CrashIDNotFound):
            self.fsrts.get_unredacted_processed(self.CRASH_ID_1)

    def test_get_raw_dump(self):
        self._make_test_crash()
        contents = self.fsrts.get_raw_dump(self.CRASH_ID_1, "foo")
        assert contents == b"bar"

        contents = self.fsrts.get_raw_dump(
            self.CRASH_ID_1, self.fsrts.config.dump_field
        )
        assert contents == b"baz"

        with pytest.raises(CrashIDNotFound):
            self.fsrts.get_raw_dump(self.CRASH_ID_2, "foo")

        with pytest.raises(IOError):
            self.fsrts.get_raw_dump(self.CRASH_ID_1, "foor")

    def test_get_raw_dumps(self):
        self._make_test_crash()
        expected = MemoryDumpsMapping(
            {"foo": b"bar", self.fsrts.config.dump_field: b"baz"}
        )
        assert self.fsrts.get_raw_dumps(self.CRASH_ID_1) == expected

        with pytest.raises(CrashIDNotFound):
            self.fsrts.get_raw_dumps(self.CRASH_ID_2)

    def test_remove(self):
        self._make_test_crash()
        self._make_test_crash(self.CRASH_ID_3)
        self.fsrts.remove(self.CRASH_ID_1)
        self.fsrts.remove(self.CRASH_ID_3)
        assert not os.path.exists(
            self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1)
        )
        with pytest.raises(CrashIDNotFound):
            self.fsrts.remove(self.CRASH_ID_2)
