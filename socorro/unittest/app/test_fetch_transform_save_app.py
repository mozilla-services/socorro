# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest import mock

from configman.dotdict import DotDict
import pytest

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp
from socorro.lib.threaded_task_manager import ThreadedTaskManager
from socorro.lib.task_manager import TaskManager


class TestFetchTransformSaveApp:
    def test_bogus_source_iter_and_worker(self):
        class TestFTSAppClass(FetchTransformSaveApp):
            def __init__(self, config):
                super().__init__(config)
                self.the_list = []

            def _setup_source_and_destination(self):
                self.queue = mock.Mock()

                def get_crashids():
                    for x in range(5):
                        yield ((x,), {})

                self.queue.new_crashes = get_crashids
                self.source = mock.Mock()
                self.destination = mock.Mock()

            def transform(self, anItem):
                self.the_list.append(anItem)

        config = DotDict(
            {
                "logger": mock.MagicMock(),
                "number_of_threads": 2,
                "maximum_queue_size": 2,
                "queue": DotDict({"crashqueue_class": None}),
                "source": DotDict({"crashstorage_class": None}),
                "destination": DotDict({"crashstorage_class": None}),
                "producer_consumer": DotDict(
                    {
                        "producer_consumer_class": TaskManager,
                        "logger": mock.MagicMock(),
                        "number_of_threads": 1,
                        "maximum_queue_size": 1,
                        "quit_on_empty_queue": True,
                    }
                ),
            }
        )

        fts_app = TestFTSAppClass(config)
        fts_app.main()
        assert len(fts_app.the_list) == 5
        assert sorted(fts_app.the_list) == [0, 1, 2, 3, 4]

    def test_bogus_source_and_destination(self):
        class NonInfiniteFTSAppClass(FetchTransformSaveApp):
            def source_iterator(self):
                # NOTE(willkg): This isn't in an infinite loop, so it ends
                for x in self.queue.new_crashes():
                    yield ((x,), {})

        class FakeQueue:
            def __init__(self, config, namespace=""):
                pass

            def new_crashes(self):
                # NOTE(willkg): these are keys in the FakeStorageSource
                crash_ids = ["1234", "1235", "1236", "1237"]
                for crash_id in crash_ids:
                    yield crash_id

        class FakeStorageSource:
            def __init__(self, config, namespace=""):
                self.store = DotDict(
                    {
                        "1234": DotDict(
                            {"ooid": "1234", "Product": "FireSquid", "Version": "1.0"}
                        ),
                        "1235": DotDict(
                            {"ooid": "1235", "Product": "ThunderRat", "Version": "1.0"}
                        ),
                        "1236": DotDict(
                            {"ooid": "1236", "Product": "Caminimal", "Version": "1.0"}
                        ),
                        "1237": DotDict(
                            {"ooid": "1237", "Product": "Fennicky", "Version": "1.0"}
                        ),
                    }
                )
                self.number_of_close_calls = 0

            def get_raw_crash(self, ooid):
                return self.store[ooid]

            def get_raw_dumps(self, ooid):
                return {"upload_file_minidump": "this is a fake dump"}

            def new_crashes(self):
                for k in self.store.keys():
                    yield k

            def close(self):
                self.number_of_close_calls += 1

        class FakeStorageDestination:
            def __init__(self, config, namespace=""):
                self.store = DotDict()
                self.dumps = DotDict()
                self.number_of_close_calls = 0

            def save_raw_crash(self, raw_crash, dump, crash_id):
                self.store[crash_id] = raw_crash
                self.dumps[crash_id] = dump

            def close(self):
                self.number_of_close_calls += 1

        config = DotDict(
            {
                "logger": mock.MagicMock(),
                "number_of_threads": 2,
                "maximum_queue_size": 2,
                "queue": DotDict({"crashqueue_class": FakeQueue}),
                "source": DotDict({"crashstorage_class": FakeStorageSource}),
                "destination": DotDict({"crashstorage_class": FakeStorageDestination}),
                "producer_consumer": DotDict(
                    {
                        "producer_consumer_class": ThreadedTaskManager,
                        "logger": mock.MagicMock(),
                        "number_of_threads": 1,
                        "maximum_queue_size": 1,
                    }
                ),
            }
        )

        fts_app = NonInfiniteFTSAppClass(config)
        fts_app.main()

        source = fts_app.source
        destination = fts_app.destination

        assert source.store == destination.store
        assert len(destination.dumps) == 4
        assert destination.dumps["1237"] == source.get_raw_dumps("1237")
        # ensure that each storage system had its close called
        assert source.number_of_close_calls == 1
        assert destination.number_of_close_calls == 1

    def test_queue_iterator(self):
        faked_finished_func = mock.Mock()

        class FakeQueue:
            def __init__(self):
                self.first = True

            def new_crashes(self):
                if self.first:
                    # make the iterator act as if exhausted on the very
                    # first try
                    self.first = False
                else:
                    for k in range(999):
                        # ensure that both forms (a single value or the
                        # (args, kwargs) form are accepted.)
                        if k % 4:
                            yield k
                        else:
                            yield ((k,), {"finished_func": faked_finished_func})
                    for k in range(2):
                        yield None

        class FakeStorageDestination:
            def __init__(self, config):
                self.store = DotDict()
                self.dumps = DotDict()

            def save_raw_crash(self, raw_crash, dump, crash_id):
                self.store[crash_id] = raw_crash
                self.dumps[crash_id] = dump

        config = DotDict(
            {
                "logger": mock.MagicMock(),
                "number_of_threads": 2,
                "maximum_queue_size": 2,
                "queue": DotDict({"crashqueue_class": FakeQueue}),
                "source": DotDict({"crashstorage_class": None}),
                "destination": DotDict({"crashstorage_class": FakeStorageDestination}),
                "producer_consumer": DotDict(
                    {
                        "producer_consumer_class": ThreadedTaskManager,
                        "logger": mock.MagicMock(),
                        "number_of_threads": 1,
                        "maximum_queue_size": 1,
                    }
                ),
            }
        )

        fts_app = FetchTransformSaveApp(config)
        fts_app.queue = FakeQueue()
        fts_app.source = None
        fts_app.destination = FakeStorageDestination
        error_detected = False
        no_finished_function_counter = 0
        for x, y in zip(range(1002), (a for a in fts_app.source_iterator())):
            if x == 0:
                # the iterator is exhausted on the 1st try and should have
                # yielded a None before starting over
                assert y is None
            elif x < 1000:
                if x - 1 != y[0][0] and not error_detected:
                    error_detected = True
                    assert x == y, "iterator fails on iteration %d: %s" % (x, y)
                # invoke that finished func to ensure that we've got the
                # right object
                try:
                    y[1]["finished_func"]()
                except KeyError:
                    no_finished_function_counter += 1
            else:
                if y is not None and not error_detected:
                    error_detected = True
                    assert x is None, "iterator fails on iteration %d: %s" % (x, y)
        assert faked_finished_func.call_count == (999 - no_finished_function_counter)

    def test_no_source(self):
        class FakeStorageDestination:
            def __init__(self, config):
                self.store = DotDict()
                self.dumps = DotDict()

            def save_raw_crash(self, raw_crash, dump, crash_id):
                self.store[crash_id] = raw_crash
                self.dumps[crash_id] = dump

        config = DotDict(
            {
                "logger": mock.MagicMock(),
                "number_of_threads": 2,
                "maximum_queue_size": 2,
                "queue": DotDict({"crashqueue_class": None}),
                "source": DotDict({"crashstorage_class": None}),
                "destination": DotDict({"crashstorage_class": FakeStorageDestination}),
                "producer_consumer": DotDict(
                    {
                        "producer_consumer_class": ThreadedTaskManager,
                        "logger": mock.MagicMock(),
                        "number_of_threads": 1,
                        "maximum_queue_size": 1,
                    }
                ),
            }
        )

        fts_app = FetchTransformSaveApp(config)

        with pytest.raises(TypeError):
            fts_app.main()

    def test_no_destination(self):
        class FakeStorageSource:
            def __init__(self, config):
                self.store = DotDict(
                    {
                        "1234": DotDict(
                            {"ooid": "1234", "Product": "FireSquid", "Version": "1.0"}
                        ),
                        "1235": DotDict(
                            {"ooid": "1235", "Product": "ThunderRat", "Version": "1.0"}
                        ),
                        "1236": DotDict(
                            {"ooid": "1236", "Product": "Caminimal", "Version": "1.0"}
                        ),
                        "1237": DotDict(
                            {"ooid": "1237", "Product": "Fennicky", "Version": "1.0"}
                        ),
                    }
                )

            def get_raw_crash(self, ooid):
                return self.store[ooid]

            def get_raw_dump(self, ooid):
                return "this is a fake dump"

            def new_ooids(self):
                for k in self.store.keys():
                    yield k

        config = DotDict(
            {
                "logger": mock.MagicMock(),
                "number_of_threads": 2,
                "maximum_queue_size": 2,
                "queue": DotDict({"crashqueue_class": None}),
                "source": DotDict({"crashstorage_class": FakeStorageSource}),
                "destination": DotDict({"crashstorage_class": None}),
                "producer_consumer": DotDict(
                    {
                        "producer_consumer_class": ThreadedTaskManager,
                        "logger": mock.MagicMock(),
                        "number_of_threads": 1,
                        "maximum_queue_size": 1,
                    }
                ),
            }
        )

        fts_app = FetchTransformSaveApp(config)

        with pytest.raises(TypeError):
            fts_app.main()
