# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import OrderedDict
import logging
import os
import sys
import tempfile

from configman import Namespace, RequiredConfig


if os.uname()[0] != "Linux":
    # You're not on Linux! Avoid pyinotify like the plague

    warning_message = (
        "SymbolLRUCache is disabled on operating systems that does not "
        "have inotify in its kernel."
    )

    class ProcessEvent:
        # Defining a class means we can't define the EventHandler class
        # without indenting the whole thing in an if-block.
        def __init__(self, *_, **__):
            # Re-use the warning as a the error message in case someone
            # missing the warning and don't understand why it's not
            # working on their Windows or OSX.
            raise NotImplementedError(warning_message)

    # Warn about the fact that SymbolLRUCache is going to be borked
    # just by trying to import this.
    import warnings

    warnings.warn(warning_message)
else:
    import pyinotify
    from pyinotify import ProcessEvent


class EventHandler(ProcessEvent):
    def __init__(self, monitor, verbosity=0):
        pyinotify.ProcessEvent.__init__(self)
        self.monitor = monitor
        self.verbosity = verbosity

    def process_IN_DELETE(self, event):
        if not event.dir:
            if self.verbosity == 1:
                sys.stdout.write("D")
                sys.stdout.flush()
            elif self.verbosity == 2:
                self.monitor.logger.debug("D  %s", event.pathname)
            self.monitor._remove_cached(event.pathname)

    def process_IN_CREATE(self, event):
        if not event.dir:
            if self.verbosity == 1:
                sys.stdout.write("C")
                sys.stdout.flush()
            elif self.verbosity == 2:
                self.monitor.logger.debug("C  %s", event.pathname)
            self.monitor._update_cache(event.pathname)

    def process_IN_MOVED_FROM(self, event):
        if not event.dir:
            if self.verbosity == 1:
                sys.stdout.write("M")
                sys.stdout.flush()
            elif self.verbosity == 2:
                self.monitor.logger.debug("M> %s", event.pathname)
            self.monitor._remove_cached(event.pathname)

    def process_IN_MOVED_TO(self, event):
        if not event.dir:
            if self.verbosity == 1:
                sys.stdout.write("M")
                sys.stdout.flush()
            elif self.verbosity == 2:
                self.monitor.logger.debug("M< %s", event.pathname)
            self.monitor._update_cache(event.pathname)

    def process_IN_OPEN(self, event):
        if not event.dir:
            if self.verbosity == 1:
                sys.stdout.write("O")
                sys.stdout.flush()
            elif self.verbosity == 2:
                self.monitor.logger.debug("O  %s", event.pathname)
            self.monitor._update_cache(event.pathname)

    def process_IN_MODIFY(self, event):
        if not event.dir:
            if self.verbosity == 1:
                sys.stdout.write("M")
                sys.stdout.flush()
            elif self.verbosity == 2:
                self.monitor.logger.debug("M  %s", event.pathname)
            self.monitor._update_cache(event.pathname, update_size=True)


def from_string_to_parse_size(size_as_string):
    """
    Parse a size argument of the form \\d+[kMG] that represents a size in
    bytes, with the suffixes representing kilobytes, megabytes or gigabytes
    respectively.
    """
    suffixes = {"k": 1024, "M": 1024 ** 2, "G": 1024 ** 3}
    if not isinstance(size_as_string, str) or not size_as_string:
        raise ValueError('Bad size value: "%s"' % size_as_string)

    if size_as_string[-1].isdigit():
        return int(size_as_string)

    if size_as_string[-1] not in suffixes:
        raise ValueError('Unknown size suffix: "%s"' % size_as_string[-1])

    return int(size_as_string[:-1]) * suffixes[size_as_string[-1]]


class SymbolLRUCacheManager(RequiredConfig):
    """for cleaning up the symbols cache"""

    required_config = Namespace()
    required_config.add_option(
        "symbol_cache_path",
        doc="the cache directory to automatically remove files from",
        default=os.path.join(tempfile.gettempdir(), "symbols"),
    )
    required_config.add_option(
        "symbol_cache_size",
        doc="the maximum size of the symbols cache",
        default="1G",
        from_string_converter=from_string_to_parse_size,
    )
    required_config.add_option(
        "verbosity",
        doc="how chatty should this be? 1 - writes to stdout," " 2 - uses the logger",
        default=0,
        from_string_converter=int,
    )

    def __init__(self, config):
        """constructor for a registration object that runs an LRU cache
       cleaner"""
        self.config = config
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

        self.directory = os.path.abspath(config.symbol_cache_path)
        self.max_size = config.symbol_cache_size
        self.verbosity = config.verbosity
        # Cache state
        self.total_size = 0
        self._lru = OrderedDict()
        # pyinotify bits
        self._wm = pyinotify.WatchManager()
        self._handler = EventHandler(self, verbosity=config.verbosity)
        self._notifier = pyinotify.ThreadedNotifier(self._wm, self._handler)
        mask = (
            pyinotify.IN_DELETE
            | pyinotify.IN_CREATE
            | pyinotify.IN_OPEN
            | pyinotify.IN_MOVED_FROM
            | pyinotify.IN_MOVED_TO
            | pyinotify.IN_MODIFY
        )
        self._wdd = self._wm.add_watch(self.directory, mask, rec=True, auto_add=True)
        # Load existing files into the cache.
        self._get_existing_files(self.directory)
        self._notifier.start()

    @property
    def num_files(self):
        return len(self._lru)

    def _rm_empty_dirs(self, path):
        """
        Attempt to remove any empty directories that are parents of path
        and children of self.directory.
        """
        path = os.path.dirname(path)
        while not os.path.samefile(path, self.directory):
            if not os.listdir(path):
                os.rmdir(path)
            path = os.path.dirname(path)

    def _update_cache(self, path, update_size=False):
        if path in self._lru:
            size = self._lru.pop(path)
            if update_size:
                self.total_size -= size
        else:
            update_size = True

        if update_size:
            try:
                size = os.stat(path).st_size
            except OSError:
                self.logger.warning("file was not found while cleaning cache: %s", path)
                return

            self.total_size += size
            # If we're out of space, remove items from the cache until
            # we fit again.
            while self.total_size > self.max_size and self._lru:
                rm_path, rm_size = self._lru.popitem(last=False)
                self.total_size -= rm_size
                os.unlink(rm_path)
                self._rm_empty_dirs(rm_path)
                if self.verbosity >= 2:
                    self.logger.debug("RM %s", rm_path)
        self._lru[path] = size

    def _remove_cached(self, path):
        # We might have already removed this file in _update_cache.
        if path in self._lru:
            size = self._lru.pop(path)
            self.total_size -= size

    def _get_existing_files(self, path):
        for base, dirs, files in os.walk(path):
            for f in files:
                f = os.path.join(base, f)
                self._update_cache(f)

    def close(self):
        self._notifier.stop()


class NoOpCacheManager(RequiredConfig):
    def __init__(self, *args, **kwargs):
        pass
