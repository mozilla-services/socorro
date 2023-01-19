# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from configman import Namespace, ConfigurationManager
import pytest

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    PolyStorageError,
    PolyCrashStorage,
    BenchmarkingCrashStorage,
    MemoryDumpsMapping,
    MetricsCounter,
    MetricsBenchmarkingWrapper,
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

    def test_polyerror(self):
        p = PolyStorageError("hell")
        try:
            try:
                raise NameError("dwight")
            except NameError:
                p.gather_current_exception()
            try:
                raise KeyError("wilma")
            except KeyError:
                p.gather_current_exception()
            try:
                raise AttributeError("sarita")
            except AttributeError:
                p.gather_current_exception()
            raise p

        except PolyStorageError as x:
            assert len(x) == 3
            assert x.has_exceptions()
            expected = [NameError, KeyError, AttributeError]
            assert [exc[0] for exc in x] == expected
            assert 1 not in x
            assert str(x[0][1]) == "dwight"
            assert all(
                sample in str(x)
                for sample in ["hell", "NameError", "KeyError", "AttributeError"]
            )
            assert (
                str(x)
                == "hell,NameError('dwight'),KeyError('wilma'),AttributeError('sarita')"
            )

            x[0] = x[1]
            assert x[0] == x[1]

    def test_polyerror_str_missing_args(self):
        p = PolyStorageError()
        try:
            try:
                raise NameError("dwight")
            except NameError:
                p.gather_current_exception()
            try:
                raise KeyError("wilma")
            except KeyError:
                p.gather_current_exception()
            raise p
        except PolyStorageError as x:
            assert str(x) == "NameError('dwight'),KeyError('wilma')"

    def test_poly_crash_storage(self):
        n = Namespace()
        n.add_option("storage", default=PolyCrashStorage)
        n.add_option("logger", default=mock.Mock())
        value = {
            "storage_namespaces": "A,A2,B",
            "A.crashstorage_class": "socorro.tests.external.test_crashstorage_base.A",
            "A2.crashstorage_class": "socorro.tests.external.test_crashstorage_base.A",
            "B.crashstorage_class": "socorro.tests.external.test_crashstorage_base.B",
            "A2.y": 37,
        }
        cm = ConfigurationManager(n, values_source_list=[value])
        with cm.context() as config:
            assert config.A.crashstorage_class.foo == "a"
            assert config.A2.crashstorage_class.foo == "a"
            assert config.A2.y == 37
            assert config.B.crashstorage_class.foo == "b"

            poly_store = config.storage(config)
            assert len(poly_store.storage_namespaces) == 3
            assert poly_store.storage_namespaces[0] == "A"
            assert poly_store.storage_namespaces[1] == "A2"
            assert poly_store.storage_namespaces[2] == "B"

            assert len(poly_store.stores) == 3
            assert poly_store.stores.A.foo == "a"
            assert poly_store.stores.A2.foo == "a"
            assert poly_store.stores.B.foo == "b"

            raw_crash = {"ooid": ""}
            dump = "12345"
            processed_crash = {"ooid": "", "product": 17}
            for v in poly_store.stores.values():
                v.save_raw_crash = mock.Mock()
                v.save_processed_crash = mock.Mock()
                v.close = mock.Mock()

            poly_store.save_raw_crash(raw_crash, dump, "")
            for v in poly_store.stores.values():
                v.save_raw_crash.assert_called_once_with(raw_crash, dump, "")

            poly_store.save_processed_crash(raw_crash, processed_crash)
            for v in poly_store.stores.values():
                v.save_processed_crash.assert_called_once_with(
                    raw_crash, processed_crash
                )

            raw_crash = {"ooid": "oaeu"}
            dump = "5432"
            processed_crash = {"ooid": "aoeu", "product": 33}

            expected = Exception("this is messed up")
            poly_store.stores["A2"].save_raw_crash = mock.Mock()
            poly_store.stores["A2"].save_raw_crash.side_effect = expected
            poly_store.stores["B"].save_processed_crash = mock.Mock()
            poly_store.stores["B"].save_processed_crash.side_effect = expected

            with pytest.raises(PolyStorageError):
                poly_store.save_raw_crash(raw_crash, dump, "")

            for v in poly_store.stores.values():
                v.save_raw_crash.assert_called_with(raw_crash, dump, "")

            with pytest.raises(PolyStorageError):
                poly_store.save_processed_crash(raw_crash, processed_crash)

            for v in poly_store.stores.values():
                v.save_processed_crash.assert_called_with(raw_crash, processed_crash)

            poly_store.stores["B"].close.side_effect = Exception
            with pytest.raises(PolyStorageError):
                poly_store.close()

            for v in poly_store.stores.values():
                v.close.assert_called_with()


class TestBench:
    def test_benchmarking_crashstore(self, caplogpp):
        caplogpp.set_level("DEBUG")

        required_config = Namespace()
        required_config.update(BenchmarkingCrashStorage.get_required_config())
        fake_crash_store = mock.Mock()

        config_manager = ConfigurationManager(
            [required_config],
            app_name="testapp",
            app_version="1.0",
            app_description="app description",
            values_source_list=[
                {"wrapped_crashstore": fake_crash_store, "benchmark_tag": "test"}
            ],
            argv_source=[],
        )

        with config_manager.context() as config:
            crashstorage = BenchmarkingCrashStorage(config, namespace="")
            crashstorage.start_timer = lambda: 0
            crashstorage.end_timer = lambda: 1
            fake_crash_store.assert_called_with(config, namespace="")

            crashstorage.save_raw_crash({}, "payload", "ooid")
            crashstorage.wrapped_crashstore.save_raw_crash.assert_called_with(
                {}, "payload", "ooid"
            )
            assert "test save_raw_crash 1" in [rec.message for rec in caplogpp.records]
            caplogpp.clear()

            crashstorage.save_processed_crash({}, {})
            crashstorage.wrapped_crashstore.save_processed_crash.assert_called_with(
                {}, {}
            )
            assert "test save_processed_crash 1" in [
                rec.message for rec in caplogpp.records
            ]
            caplogpp.clear()

            crashstorage.get_raw_crash("uuid")
            crashstorage.wrapped_crashstore.get_raw_crash.assert_called_with("uuid")
            assert "test get_raw_crash 1" in [rec.message for rec in caplogpp.records]
            caplogpp.clear()

            crashstorage.get_raw_dump("uuid")
            crashstorage.wrapped_crashstore.get_raw_dump.assert_called_with("uuid")
            assert "test get_raw_dump 1" in [rec.message for rec in caplogpp.records]
            caplogpp.clear()

            crashstorage.get_dumps("uuid")
            crashstorage.wrapped_crashstore.get_dumps.assert_called_with("uuid")
            assert "test get_dumps 1" in [rec.message for rec in caplogpp.records]
            caplogpp.clear()

            crashstorage.get_dumps_as_files("uuid")
            crashstorage.wrapped_crashstore.get_dumps_as_files.assert_called_with(
                "uuid"
            )
            assert "test get_dumps_as_files 1" in [
                rec.message for rec in caplogpp.records
            ]
            caplogpp.clear()

            crashstorage.get_processed("uuid")
            crashstorage.wrapped_crashstore.get_processed.assert_called_with("uuid")
            assert "test get_processed 1" in [rec.message for rec in caplogpp.records]


class TestDumpsMappings:
    def test_simple(self):
        mdm = MemoryDumpsMapping(
            {"upload_file_minidump": b"binary_data", "moar_dump": b"more binary data"}
        )
        assert mdm.as_memory_dumps_mapping() is mdm
        fdm = mdm.as_file_dumps_mapping("a", "/tmp", "dump")
        assert fdm.as_file_dumps_mapping() is fdm
        assert fdm.as_memory_dumps_mapping() == mdm


class TestMetricsCounter:
    def test_count(self, metricsmock):
        config_manager = ConfigurationManager(
            [MetricsCounter.get_required_config()],
            values_source_list=[{"metrics_prefix": "phil", "active_list": "run"}],
            argv_source=[],
        )
        with config_manager.context() as config:
            counter = MetricsCounter(config)

        with metricsmock as mm:
            counter.run()
            counter.walk()

        mm.assert_incr_once("phil.run", value=1)


class TestMetricsBenchmarkingWrapper:
    def test_wrapper(self, metricsmock):
        fake_crash_store_class = mock.MagicMock()
        fake_crash_store_class.__name__ = "Phil"

        config_manager = ConfigurationManager(
            [MetricsBenchmarkingWrapper.get_required_config()],
            values_source_list=[
                {
                    "wrapped_object_class": fake_crash_store_class,
                    "metrics_prefix": "phil",
                    "active_list": "run",
                }
            ],
            argv_source=[],
        )
        with config_manager.context() as config:
            mbw = MetricsBenchmarkingWrapper(config)

        with metricsmock as mm:
            mbw.run()
            mbw.walk()

        mm.assert_timing_once("phil.Phil.run")

        # Assert that the wrapped crash storage class .run() and .walk() were
        # called on the instance
        fake_crash_store_class.return_value.run.assert_called_with()
        fake_crash_store_class.return_value.walk.assert_called_with()
