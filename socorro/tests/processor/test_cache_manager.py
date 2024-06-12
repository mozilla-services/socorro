# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pathlib
import time
from unittest.mock import ANY

from fillmore.test import diff_structure
from markus.testing import MetricsMock
import pytest

from socorro import settings
from socorro.processor.cache_manager import (
    count_sentry_scrub_error,
    DiskCacheManager,
    get_index,
    LastUpdatedOrderedDict,
)


@pytest.mark.parametrize(
    "sorted_list, percent, expected",
    [
        (None, 50, None),
        ([], 50, None),
        ([1], 50, 1),
        ([1, 2, 3], 50, 2),
        ([1, 2, 3, 4], 50, 2),
        ([1, 2, 3, 4], 95, 4),
    ],
)
def test_get_index(sorted_list, percent, expected):
    assert get_index(sorted_list, percent) == expected


def test_get_index_bad_percent():
    with pytest.raises(ValueError):
        get_index([1, 2, 3], -1)

    with pytest.raises(ValueError):
        get_index([1, 2, 3], 101)


class TestLastUpdatedOrderedDict:
    def test_set(self):
        lru = LastUpdatedOrderedDict()

        lru["key1"] = 1
        lru["key2"] = 2
        assert list(lru.items()) == [("key1", 1), ("key2", 2)]

        lru["key1"] = 3
        assert list(lru.items()) == [("key2", 2), ("key1", 3)]

    def test_touch(self):
        lru = LastUpdatedOrderedDict()

        lru["key1"] = 1
        lru["key2"] = 2

        lru.touch("key1")
        assert list(lru.items()) == [("key2", 2), ("key1", 1)]

    def test_popoldest(self):
        lru = LastUpdatedOrderedDict()

        lru["key1"] = 1
        lru["key2"] = 2

        oldest = lru.pop_oldest()
        assert oldest == ("key1", 1)
        assert list(lru.items()) == [("key2", 2)]


@pytest.fixture
def cm(tmp_path):
    """Test cache manager setup with tmp_path."""
    with settings.override(
        SYMBOLS_CACHE_PATH=str(tmp_path),
        SYMBOLS_CACHE_MAX_SIZE=10,
    ):
        cache_manager = DiskCacheManager()
        cache_manager.set_up()
        yield cache_manager
        cache_manager.shutdown()
        del cache_manager


def test_no_existing_files(cm, tmp_path):
    cm.run_once()

    assert len(cm.lru) == 0
    assert cm.total_size == 0


def test_existing_files(cm, tmp_path):
    pathlib.Path(tmp_path / "xul__ABCDE.symc").write_bytes(b"abcde")
    pathlib.Path(tmp_path / "xul__01234.symc").write_bytes(b"abcdef")

    cm.run_once()

    assert len(cm.lru) == 2
    assert cm.total_size == 11


def test_addfiles(cm, tmp_path):
    print(f"test {tmp_path = }")
    cm.run_once()

    # We've got a fresh cache manager with nothing in it
    assert cm.lru == {}
    assert cm.total_size == 0

    # Add one 5-byte file and run loop and make sure it's in the LRU
    file1 = pathlib.Path(tmp_path / "xul__5byte.symc")
    file1.write_bytes(b"abcde")
    cm.run_once()
    assert cm.lru == {str(file1): 5}
    assert cm.total_size == 5

    # Add one 4-byte file and run loop and now we've got two files in the LRU
    file2 = pathlib.Path(tmp_path / "xul__4byte.symc")
    file2.write_bytes(b"abcd")
    cm.run_once()
    assert cm.lru == {str(file1): 5, str(file2): 4}
    assert cm.total_size == 9


def test_eviction_when_too_big(cm, tmp_path):
    cm.run_once()

    # We've got a fresh cache manager with nothing in it
    assert cm.lru == {}
    assert cm.total_size == 0

    # Add one 5-byte file and run loop and make sure it's in the LRU
    file1 = tmp_path / "xul__5byte.symc"
    file1.write_bytes(b"abcde")

    # Add one 4-byte file and run loop and now we've got two files in the LRU
    file2 = tmp_path / "xul__4byte.symc"
    file2.write_bytes(b"abcd")
    cm.run_once()
    assert cm.lru == {str(file1): 5, str(file2): 4}
    assert cm.total_size == 9

    # Add 1-byte file which gets total size to 10
    file3 = tmp_path / "xul__3byte.symc"
    file3.write_bytes(b"a")
    cm.run_once()
    assert cm.lru == {str(file1): 5, str(file2): 4, str(file3): 1}
    assert cm.total_size == 10

    # Add file4 of 6 bytes should evict file1 and file2
    file4 = tmp_path / "xul__6byte.symc"
    file4.write_bytes(b"abcdea")
    cm.run_once()
    assert cm.lru == {str(file3): 1, str(file4): 6}
    assert cm.total_size == 7

    # Verify what's in the cache dir on disk
    files = [str(path) for path in tmp_path.iterdir()]
    assert sorted(files) == sorted([str(file3), str(file4)])


def test_eviction_of_least_recently_used(cm, tmp_path):
    cm.run_once()

    # We've got a fresh cache manager with nothing in it
    assert cm.lru == {}
    assert cm.total_size == 0

    # Add some files
    file1 = tmp_path / "xul__rose.symc"
    file1.write_bytes(b"ab")

    file2 = tmp_path / "xul__dandelion.symc"
    file2.write_bytes(b"ab")

    file3 = tmp_path / "xul__orchid.symc"
    file3.write_bytes(b"ab")

    file4 = tmp_path / "xul__iris.symc"
    file4.write_bytes(b"ab")

    # Run events and verify LRU
    cm.run_once()
    assert cm.lru == {str(file1): 2, str(file2): 2, str(file3): 2, str(file4): 2}
    assert cm.total_size == 8

    # Access rose so it's recently used
    time.sleep(0.5)
    file1.read_bytes()

    # Add new file which will evict files--but not rose which was accessed
    # most recently
    file5 = tmp_path / "xul__marigold.symc"
    file5.write_bytes(b"abcdef")
    cm.run_once()
    assert cm.lru == {str(file1): 2, str(file4): 2, str(file5): 6}
    assert cm.total_size == 10

    # Verify what's in the cache dir on disk
    files = [str(path) for path in tmp_path.iterdir()]
    assert sorted(files) == sorted([str(file1), str(file4), str(file5)])


def test_add_file(cm, tmp_path):
    cm.run_once()
    assert cm.lru == {}

    file1 = tmp_path / "file1.symc"
    file1.write_bytes(b"abcde")
    cm.run_once()
    assert cm.lru == {str(file1): 5}


def test_delete_file(cm, tmp_path):
    cm.run_once()

    file1 = tmp_path / "file1.symc"
    file1.write_bytes(b"abcde")
    cm.run_once()
    assert cm.lru == {str(file1): 5}

    file1.unlink()
    cm.run_once()
    assert cm.lru == {}


def test_moved(cm, tmp_path):
    cm.run_once()
    assert cm.lru == {}
    assert cm.total_size == 0

    file1 = tmp_path / "file1.symc"
    file1.write_bytes(b"abcde")
    cm.run_once()
    assert cm.lru == {str(file1): 5}
    assert cm.total_size == 5

    dest_file1 = tmp_path / "file1_copied.symc"
    file1.rename(dest_file1)
    cm.run_once()
    assert cm.lru == {str(dest_file1): 5}
    assert cm.total_size == 5


def test_nested_directories(cm, tmp_path):
    cm.run_once()
    assert cm.lru == {}

    dir1 = tmp_path / "dir1"
    dir1.mkdir()

    # Run to pick up the new subdirectory and watch it
    cm.run_once()

    subdir1 = dir1 / "subdir1"
    subdir1.mkdir()

    # Run to pick up the new subsubdirectory and watch it
    cm.run_once()

    # Create two files in the subsubdirectory with 9 bytes
    file1 = subdir1 / "file1.symc"
    file1.write_bytes(b"abcde")

    time.sleep(0.5)

    file2 = subdir1 / "file2.symc"
    file2.write_bytes(b"abcd")

    cm.run_once()
    assert cm.lru == {str(file1): 5, str(file2): 4}

    # Add a new file with 2 bytes that puts it over the edge
    file3 = dir1 / "file3.symc"
    file3.write_bytes(b"ab")

    cm.run_once()
    assert cm.lru == {str(file2): 4, str(file3): 2}


def test_nested_directories_evict(cm, tmp_path):
    cm.run_once()
    assert cm.lru == {}

    dir1 = tmp_path / "dir1"
    dir1.mkdir()

    # Run to pick up the new subdirectory and watch it
    cm.run_once()

    subdir1 = dir1 / "subdir1"
    subdir1.mkdir()

    subdir2 = dir1 / "subdir2"
    subdir2.mkdir()

    # Run to pick up new subsubdirectories and watch them
    time.sleep(0.5)
    cm.run_once()

    # Create two files in the subsubdirectory with 9 bytes
    file1 = subdir1 / "file1.symc"
    file1.write_bytes(b"abcde")

    file2 = subdir2 / "file2.symc"
    file2.write_bytes(b"abcd")

    time.sleep(0.5)
    cm.run_once()
    assert cm.lru == {str(file1): 5, str(file2): 4}

    # Add a new file with 2 bytes that puts it over the edge
    file3 = dir1 / "file3.symc"
    file3.write_bytes(b"ab")

    # Run to handle CREATE file3 which kicks off the eviction
    cm.run_once()

    # Run to handle DELETE | ISDIR for subdir1
    cm.run_once()
    assert cm.lru == {str(file2): 4, str(file3): 2}
    assert list(cm.watches.keys()) == [
        str(tmp_path),
        str(dir1),
        # subdir1 is out because there are no files in it
        str(subdir2),
    ]


# NOTE(willkg): If this changes, we should update it and look for new things that should
# be scrubbed. Use ANY for things that change between tests.
BROKEN_EVENT = {
    "breadcrumbs": ANY,
    "contexts": {
        "runtime": {
            "build": ANY,
            "name": "CPython",
            "version": ANY,
        },
        "trace": {
            "parent_span_id": None,
            "span_id": ANY,
            "trace_id": ANY,
        },
    },
    "environment": "production",
    "event_id": ANY,
    "exception": {
        "values": [
            {
                "mechanism": {"handled": True, "type": "logging"},
                "module": None,
                "stacktrace": {
                    "frames": [
                        {
                            "abs_path": "/app/socorro/processor/cache_manager.py",
                            "context_line": ANY,
                            "filename": "socorro/processor/cache_manager.py",
                            "function": "_event_generator",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "socorro.processor.cache_manager",
                            "post_context": ANY,
                            "pre_context": ANY,
                            "vars": ANY,
                        },
                        {
                            "abs_path": "/app/socorro/tests/processor/test_cache_manager.py",
                            "context_line": ANY,
                            "filename": "socorro/tests/processor/test_cache_manager.py",
                            "function": "mock_make_room",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "socorro.tests.processor.test_cache_manager",
                            "post_context": ANY,
                            "pre_context": ANY,
                            "vars": ANY,
                        },
                    ]
                },
                "type": "Exception",
                "value": "intentional exception",
            }
        ]
    },
    "extra": {
        "asctime": ANY,
        "processname": "main",
        "sys.argv": ANY,
    },
    "level": "error",
    "logentry": {
        "message": "Exception thrown while handling events: %s",
        "params": ["Exception('intentional exception')"],
    },
    "logger": "socorro.processor.cache_manager.DiskCacheManager",
    "modules": ANY,
    "platform": "python",
    "release": ANY,
    "sdk": {
        "integrations": [
            "argv",
            "atexit",
            "dedupe",
            "excepthook",
            "logging",
            "modules",
            "stdlib",
            "threading",
        ],
        "name": "sentry.python",
        "packages": [
            {
                "name": "pypi:sentry-sdk",
                "version": ANY,
            }
        ],
        "version": ANY,
    },
    "server_name": ANY,
    "timestamp": ANY,
    "transaction_info": {},
}


def test_sentry_scrubbing(sentry_helper, cm, monkeypatch, tmp_path):
    """Test sentry scrubbing configuration

    This verifies that the scrubbing configuration is working by using the /__broken__
    view to trigger an exception that causes Sentry to emit an event for.

    This also helps us know when something has changed when upgrading sentry_sdk that
    would want us to update our scrubbing code or sentry init options.

    This test will fail whenever we:

    * update sentry_sdk to a new version
    * update configuration which will changing the logging breadcrumbs

    In those cases, we should copy the new event, read through it for new problems, and
    redact the parts that will change using ANY so it passes tests.

    """

    # Mock out "make_room" so we can force the cache manager to raise an exception in
    # the area it might raise a real exception
    def mock_make_room(*args, **kwargs):
        raise Exception("intentional exception")

    monkeypatch.setattr(cm, "make_room", mock_make_room)

    with sentry_helper.reuse() as sentry_client:
        # Add some files to trigger the make_room call
        file1 = tmp_path / "xul__5byte.symc"
        file1.write_bytes(b"abcde")
        cm.run_once()
        file2 = tmp_path / "xul__4byte.symc"
        file2.write_bytes(b"abcd")
        cm.run_once()

        (event,) = sentry_client.envelope_payloads

        # Drop the "_meta" bit because we don't want to compare that.
        del event["_meta"]

        # Assert that the event is what we expected
        differences = diff_structure(event, BROKEN_EVENT)
        assert differences == []


def test_count_sentry_scrub_error():
    with MetricsMock() as metricsmock:
        metricsmock.clear_records()
        count_sentry_scrub_error("foo")
        metricsmock.assert_incr(
            "processor.sentry_scrub_error", value=1, tags=["service:cachemanager"]
        )
