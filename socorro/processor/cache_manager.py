#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This defines the DiskCacheManager application. It's designed to run as a standalone
application separate from the rest of the processor.

It keeps track of files in a directory and evicts files least recently used in order to
keep the total size under a max number.

It uses inotify to cheaply watch the files.

It pulls all its configuration from socorro.settings.

To run::

    $ /app/bin/run_cache_manager.sh

"""

from collections import OrderedDict
import logging
import os
import pathlib
import sys
import time
import traceback

from boltons.dictutils import OneToOne
from fillmore.libsentry import set_up_sentry
from fillmore.scrubber import Scrubber, SCRUB_RULES_DEFAULT
from inotify_simple import INotify, flags, Event

from socorro import settings
from socorro.libmarkus import METRICS, set_up_metrics
from socorro.lib.libdockerflow import get_release_name, get_version_info
from socorro.lib.liblogging import set_up_logging


# How many errors before we give up and terminate the process
MAX_ERRORS = 10

# How many seconds between heartbeats
HEARTBEAT_INTERVAL = 60


def count_sentry_scrub_error(msg):
    # NOTE(willkg): we re-use the processor prefix here and differentiate with the
    # service tag.
    METRICS.incr("processor.sentry_scrub_error", value=1, tags=["service:cachemanager"])


class LastUpdatedOrderedDict(OrderedDict):
    """Store items in the order the keys were last added or updated"""

    def __setitem__(self, key, value):
        """Create or update a key"""
        super().__setitem__(key, value)
        self.move_to_end(key, last=True)

    def touch(self, key):
        """Update last-updated for key"""
        self.move_to_end(key, last=True)

    def pop_oldest(self):
        """Pop the oldest item"""
        return self.popitem(last=False)


def handle_exception(exctype, value, tb):
    logger = logging.getLogger(__name__)
    logger.error(
        "unhandled exception. Exiting. "
        + "".join(traceback.format_exception(exctype, value, tb))
    )


sys.excepthook = handle_exception


def get_index(sorted_list, percent):
    """Given a sorted list, return the percentth item.

    :args sorted_list: sorted list of things
    :args percent: the percentth item (low) to retrieve in the sorted list

    :returns: the percentth item or None if the list is empty

    Examples:

    >>> get_index([], 50)
    None
    >>> get_index([1, 2, 3], 50)
    2
    >>> get_index([1, 2, 3, 4], 50)
    2

    """
    if not sorted_list:
        return None

    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")

    index = int(len(sorted_list) * percent / 100)
    if index > 0 and index % 2 == 0:
        index -= 1
    return sorted_list[index]


class DiskCacheManager:
    def __init__(self):
        self.basedir = pathlib.Path(__file__).resolve().parent.parent.parent
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

        self.cachepath = pathlib.Path(settings.SYMBOLS_CACHE_PATH).resolve()
        self.max_size = settings.SYMBOLS_CACHE_MAX_SIZE
        if self.max_size is None:
            raise ValueError("SYMBOLS_CACHE_MAX_SIZE must have non-None value")

        # Set up attributes for cache monitoring; these get created in the generator
        self.lru = LastUpdatedOrderedDict()
        self.total_size = 0
        self.watches = OneToOne()
        self._generator = None
        self.inotify = None
        self.watch_flags = (
            flags.CREATE
            | flags.DELETE
            | flags.DELETE_SELF
            | flags.MODIFY
            | flags.MOVED_FROM
            | flags.MOVED_TO
            | flags.OPEN
        )

        # If the logging level is DEBUG, then we'll treat that as meaning we should be
        # in verbose mode and emit additional run information
        self.is_verbose = settings.CACHE_MANAGER_LOGGING_LEVEL == "DEBUG"

    def set_up(self):
        set_up_logging(
            local_dev_env=settings.LOCAL_DEV_ENV,
            logging_level=settings.CACHE_MANAGER_LOGGING_LEVEL,
            hostname=settings.HOSTNAME,
        )
        set_up_metrics(
            statsd_host=settings.STATSD_HOST,
            statsd_port=settings.STATSD_PORT,
            hostname=settings.HOSTNAME,
            debug=settings.LOCAL_DEV_ENV,
        )

        scrubber = Scrubber(
            rules=SCRUB_RULES_DEFAULT,
            error_handler=count_sentry_scrub_error,
        )
        set_up_sentry(
            sentry_dsn=settings.SENTRY_DSN,
            release=get_release_name(self.basedir),
            host_id=settings.HOSTNAME,
            before_send=scrubber,
        )

        self.log_config()

        # Create the cachepath if we need to
        self.cachepath.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "starting up; watching: %s, max size: %s",
            str(self.cachepath),
            f"{self.max_size:,d}",
        )

    def log_config(self):
        version_info = get_version_info(self.basedir)
        data = ", ".join(
            [f"{key!r}: {val!r}" for key, val in sorted(version_info.items())]
        )
        data = data or "no version data"
        self.logger.info("version.json: %s", data)
        settings.log_settings(logger=self.logger)

    def add_watch(self, path):
        """Add a watch

        :arg path: the absolute path to the directory to add a watch to

        :returns: the watch descriptor for the path

        :raises OSError: if inotify was unable to add the watch, possibly because
            the file does not exist

        """
        path = str(path)
        if path not in self.watches:
            wd = self.inotify.add_watch(path, self.watch_flags)
            self.watches[path] = wd
        return self.watches[path]

    def remove_watch(self, path):
        """Remove a watch

        :arg path: the absolute path to the directory to remove a watch from

        :raises OSError:

        """
        if path in self.watches:
            wd = self.watches.pop(path)
            self.inotify.rm_watch(wd)

    def inventory_existing(self, path):
        """Add contents of path to LRU

        This goes through the contents of the path, adds watches for directories, and
        adds files to the LRU.

        NOTE(willkg): This does not deal with the max size of the LRU--that'll get
        handled when we start going through events.

        :arg path: a str or Path of the path to inventory

        """
        cachepath = str(path)

        for base, dirs, files in os.walk(cachepath):
            for dir_ in dirs:
                path = os.path.join(base, dir_)
                if path not in self.watches:
                    try:
                        self.add_watch(path)
                        self.logger.debug("adding watch: %s", path)
                    except OSError:
                        self.logger.exception("unable to add watch %s", path)

            for fn in files:
                path = os.path.join(base, fn)
                if path not in self.lru:
                    # Add the file if it's there. If not, ignore the error and move
                    # on.
                    try:
                        size = os.stat(path).st_size
                    except OSError:
                        continue
                    self.lru[path] = size
                    self.total_size += size
                    self.logger.debug("adding file: %s (%s)", path, f"{size:,d}")

    def make_room(self, size):
        total_size = self.total_size + size
        removed = 0

        while self.lru and total_size > self.max_size:
            rm_path, rm_size = self.lru.pop_oldest()
            total_size -= rm_size
            removed += rm_size
            try:
                # Delete the evicted file
                os.remove(rm_path)
            except FileNotFoundError:
                # If there was an OSError, then this file is gone already. We need to
                # update our bookkeping, so continue.
                pass
            try:
                # Attempt to prune empty directories. This will trigger DELETE | ISDIR
                # events and get cleaned up by the event loop.
                os.removedirs(os.path.dirname(rm_path))
            except OSError:
                continue

            self.logger.debug("evicted %s %s", rm_path, f"{rm_size:,d}")
            METRICS.incr("processor.cache_manager.evict")

        self.total_size -= removed

    def _event_generator(self, nonblocking=False):
        """Returns a generator of inotify events."""
        is_verbose = self.is_verbose
        logger = self.logger

        if nonblocking:
            # NOTE(willkg): Timeout of 0 should return immediately if there's nothing
            # there
            timeout = 0
        else:
            timeout = 500

        self.inotify = INotify(nonblocking=nonblocking)

        # Set up watches and LRU with what exists already
        self.watches = OneToOne()
        self.lru = LastUpdatedOrderedDict()
        self.total_size = 0

        self.add_watch(self.cachepath)
        self.inventory_existing(self.cachepath)

        logger.info("found %s files (%s bytes)", len(self.lru), f"{self.total_size:,d}")
        logger.info("entering loop")

        self.running = True
        processed_events = False
        num_unhandled_errors = 0
        next_heartbeat = time.time() + HEARTBEAT_INTERVAL
        try:
            while self.running:
                try:
                    events = self.inotify.read(timeout=timeout)
                    while events:
                        event = events.pop(0)

                        processed_events = True
                        event_mask = event.mask

                        if is_verbose:
                            flags_list = ", ".join(
                                [str(flag) for flag in flags.from_mask(event_mask)]
                            )
                            if event.wd > 0:
                                try:
                                    dir_path = self.watches.inv[event.wd]
                                except KeyError:
                                    dir_path = ""
                            else:
                                dir_path = ""
                            logger.debug(
                                "EVENT: PATH:%s/%s %s: %s",
                                dir_path,
                                event.name,
                                event,
                                flags_list,
                            )

                        if flags.IGNORED & event_mask:
                            continue

                        if flags.Q_OVERFLOW & event_mask:
                            METRICS.incr("processor.cache_manager.q_overflow")
                            continue

                        try:
                            dir_path = self.watches.inv[event.wd]
                        except KeyError:
                            # If there's a key error, it means that this wd is no longer
                            # being tracked, so we can ignore this event
                            continue

                        path = os.path.join(dir_path, event.name)

                        if flags.ISDIR & event_mask:
                            # Handle directory events which update our watch lists
                            if flags.CREATE & event_mask:
                                try:
                                    created_wd = self.add_watch(path)
                                except OSError:
                                    logger.exception("add watch error for %s", path)
                                    continue

                                # This is a new directory to watch, so we add faked
                                # events for subdirectories and files
                                for name in os.listdir(path):
                                    sub_path = os.path.join(path, name)

                                    if os.path.isdir(sub_path):
                                        if sub_path in self.watches:
                                            # If it's already being watched somehow,
                                            # skip it
                                            continue
                                        sub_event_flags = flags.CREATE | flags.ISDIR
                                    elif os.path.isfile(sub_path):
                                        if sub_path in self.lru:
                                            # If it's already in the lru somehow, skip
                                            # it
                                            continue
                                        sub_event_flags = flags.CREATE
                                    else:
                                        # If this isn't a file or dir, then skip it
                                        continue

                                    events.insert(
                                        0,
                                        Event(created_wd, sub_event_flags, None, name),
                                    )

                            elif flags.DELETE_SELF & event_mask:
                                if path in self.watches:
                                    try:
                                        self.remove_watch(path)
                                    except OSError:
                                        continue

                            elif flags.DELETE & event_mask:
                                if path in self.watches:
                                    try:
                                        self.remove_watch(path)
                                    except OSError:
                                        continue

                        else:
                            # Handle file events which update our LRU cache
                            if flags.CREATE & event_mask:
                                if path not in self.lru:
                                    try:
                                        size = os.stat(path).st_size
                                    except FileNotFoundError:
                                        # The file was created and deleted in rapid
                                        # succession, so we can ignore it
                                        continue

                                    self.make_room(size)
                                    self.lru[path] = size
                                    self.total_size += size

                            elif flags.OPEN & event_mask:
                                if path in self.lru:
                                    self.lru.touch(path)

                            elif flags.MODIFY & event_mask:
                                size = self.lru[path]
                                try:
                                    new_size = os.stat(path).st_size
                                except FileNotFoundError:
                                    # The file was modified and deleted in rapid
                                    # succession, so we treat it as a delete
                                    size = self.lru.pop(path)
                                    self.total_size -= size
                                    continue

                                if size != new_size:
                                    self.total_size -= size
                                    self.make_room(new_size)
                                    self.total_size += new_size

                                self.lru[path] = new_size

                            elif flags.DELETE & event_mask:
                                if path in self.lru:
                                    # NOTE(willkg): DELETE can be triggered by an
                                    # external thing or by the disk cache manager, so it
                                    # may or may not be in the lru
                                    size = self.lru.pop(path)
                                    self.total_size -= size

                            elif flags.MOVED_TO & event_mask:
                                if path not in self.lru:
                                    # If the path isn't in self.lru, then treat this
                                    # like a create
                                    try:
                                        size = os.stat(path).st_size
                                    except FileNotFoundError:
                                        # The file was created and deleted in rapid
                                        # succession, so we can ignore it
                                        continue
                                    self.make_room(size)
                                    self.lru[path] = size
                                    self.total_size += size

                            elif flags.MOVED_FROM & event_mask:
                                if path in self.lru:
                                    # If it was moved out of this directory, then treat
                                    # it like a DELETE
                                    size = self.lru.pop(path)
                                    self.total_size -= size

                            else:
                                if is_verbose:
                                    logger.debug("unhandled event: %s %s", path, event)

                except Exception as exc:
                    logger.exception("Exception thrown while handling events: %s", exc)

                    # If there are more than 10 unhandled errors, it's probably
                    # something seriously wrong and the loop should terminate
                    num_unhandled_errors += 1
                    if num_unhandled_errors >= MAX_ERRORS:
                        logger.error("Exceeded maximum number of errors.")
                        raise

                # Only do this work if in verbose mode; we get disk usage metrics via
                # other methods in server environments
                if is_verbose and processed_events:
                    logger.debug(
                        "lru: count %d, size %s",
                        len(self.lru),
                        f"{self.total_size:,d}",
                    )
                    processed_events = False

                # Emit usage metric, but debounce it so it only gets emitted at most
                # once per HEARTBEAT_INTERVAL
                now = time.time()
                if now > next_heartbeat:
                    if is_verbose:
                        METRICS.gauge(
                            "processor.cache_manager.usage", value=self.total_size
                        )

                    if self.lru:
                        sorted_sizes = list(sorted(self.lru.values()))
                        avg = int(sum(sorted_sizes) / len(sorted_sizes))
                        # Some metrics about file sizes
                        METRICS.gauge("processor.cache_manager.file_sizes.avg", avg)
                        METRICS.gauge(
                            "processor.cache_manager.file_sizes.median",
                            get_index(sorted_sizes, 50),
                        )
                        METRICS.gauge(
                            "processor.cache_manager.file_sizes.ninety_five",
                            get_index(sorted_sizes, 95),
                        )
                        METRICS.gauge(
                            "processor.cache_manager.file_sizes.max", sorted_sizes[-1]
                        )

                        # Some metrics about what's in the cache
                        METRICS.gauge(
                            "processor.cache_manager.files.count", len(sorted_sizes)
                        )
                        gt_500 = len([fs for fs in sorted_sizes if fs > 500_000_000])
                        METRICS.gauge("processor.cache_manager.files.gt_500", gt_500)

                    next_heartbeat = now + HEARTBEAT_INTERVAL

                yield

        finally:
            all_watches = list(self.watches.inv.keys())
            for wd in all_watches:
                try:
                    self.inotify.rm_watch(wd)
                except Exception:
                    # We're ending the loop, so if there's some exception, we should
                    # print it but move on.
                    self.logger.exception("Exception thrown while removing watches")

        self.inotify.close()

    def run_loop(self):
        """Run cache manager in a loop."""
        if self._generator is None:
            self._generator = self._event_generator()

        while True:
            next(self._generator)

        self.shutdown()

    def run_once(self):
        """Runs a nonblocking event generator once."""
        if self._generator is None:
            self._generator = self._event_generator(nonblocking=True)

        return next(self._generator)

    def shutdown(self):
        """Shut down an event generator."""
        if self._generator:
            # Stop the generator loop
            self.running = False
            generator = self._generator
            self._generator = None
            try:
                # Run the generator one more time so it exits the loop and closes
                # the FileIO
                next(generator)
            except StopIteration:
                pass


def main():
    app = DiskCacheManager()
    app.set_up()
    app.run_loop()


if __name__ == "__main__":
    # NOTE(willkg): we need to do this so that the cache_manager logger isn't `__main__`
    # which causes problems when logging
    from socorro.processor import cache_manager

    cache_manager.main()
