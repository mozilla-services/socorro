# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""The classes defined herein store crash data in a file system.  This is the
original method of long term storage used by Socorro in the 2007-2010 time
frame prior to the adoption of HBase.  Crashes are stored in a radix directory
tree based on pairs of characters from the crashes' crash_id.  In addition, a
second tree of directories stores symbolic links to the crashes in a date
based hierarchy.

There are three classes defined in this file (as of 2012).  Each one derives
from the previous and adds capablities.  See the doc strings for more detail"""

import stat
import os
import json
import datetime

from configman import Namespace

from socorro.external.filesystem.json_dump_storage import (JsonDumpStorage,
                                                           NoSuchUuidFound)
from socorro.external.filesystem.processed_dump_storage import \
                                                ProcessedDumpStorage
from socorro.external.crashstorage_base import (CrashStorageBase,
                                                CrashIDNotFound)
from socorro.lib.util import DotDict
from socorro.collector.throttler import LegacyThrottler


#==============================================================================
class FileSystemRawCrashStorage(CrashStorageBase):
    """This crash storage class impements only the raw crash part of the
    api.  Raw crashes (the json file and the binary dump) are stored in a
    file system.  This class is appropriate for fast storage of crashes into
    a local file system.  In 2011, a varient of this code base was adopted
    by the Socorro Collector for fast temporary storage as crashes came in."""

    required_config = Namespace()
    required_config.add_option(
        'std_fs_root',
        doc='a path to a local file system',
        default='/home/socorro/primaryCrashStore'
    )
    required_config.add_option(
        'dump_dir_count',
        doc='the number of dumps to be stored in a single directory in the '
            'local file system',
        default=1024
    )
    required_config.add_option(
        'dump_gid',
        doc='the group ID for saved crashes in local file system (optional)',
        default=''
    )
    required_config.add_option(
        'dump_permissions',
        doc='a number used for permissions crash dump files in the local '
            'file system',
        default=stat.S_IRGRP | stat.S_IWGRP | stat.S_IRUSR | stat.S_IWUSR
    )
    required_config.add_option(
        'dir_permissions',
        doc='a number used for permissions for directories in the local '
            'file system',
        default=(stat.S_IRGRP | stat.S_IXGRP | stat.S_IWGRP | stat.S_IRUSR
                              | stat.S_IXUSR | stat.S_IWUSR)
    )
    required_config.add_option(
        'json_file_suffix',
        doc='the suffix used to identify a json file',
        default='.json'
    )
    required_config.add_option(
        'dump_file_suffix',
        doc='the suffix used to identify a dump file',
        default='.dump'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(FileSystemRawCrashStorage, self).__init__(config)
        self.std_crash_store = JsonDumpStorage(
          root=config.std_fs_root,
          maxDirectoryEntries=config.dump_dir_count,
          jsonSuffix=config.json_file_suffix,
          dumpSuffix=config.dump_file_suffix,
          dumpGID=config.dump_gid,
          dumpPermissions=config.dump_permissions,
          dirPermissions=config.dir_permissions,
          logger=config.logger
        )
        self.hostname = os.uname()[1]

    #--------------------------------------------------------------------------
    def _load_raw_crash_from_file(self, pathname):
        with open(pathname) as json_file:
            raw_crash = json.load(json_file, object_hook=DotDict)
        return raw_crash

    #--------------------------------------------------------------------------
    def _do_save_raw(self, json_storage_system, raw_crash, dump, crash_id):
        try:
            json_file_handle, dump_file_handle = json_storage_system.newEntry(
              crash_id,
              self.hostname,  # from base class
            )
            try:
                dump_file_handle.write(dump)
                json.dump(raw_crash, json_file_handle)
            finally:
                dump_file_handle.close()
                json_file_handle.close()
            self.logger.debug('saved - %s', crash_id)
        except Exception:
            self.logger.critical('storage has failed for: %s',
                                 crash_id, exc_info=True)
            raise

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dump, crash_id):
        """forward the raw_crash and the dump to the underlying file system"""
        self._do_save_raw(self.std_crash_store, raw_crash, dump, crash_id)

    #--------------------------------------------------------------------------
    def get_raw_crash(self, crash_id):
        """fetch the raw crash from the underlying file system"""
        try:
            pathname = self.std_crash_store.getJson(crash_id)
            return self._load_raw_crash_from_file(pathname)
        except OSError:
            raise CrashIDNotFound(crash_id)
        except ValueError:  # empty json file?
            return DotDict()

    #--------------------------------------------------------------------------
    def get_raw_dump(self, crash_id):
        """read the binary crash dump from the underlying file system by
        getting the pathname and then opening and reading the file."""
        try:
            job_pathname = self.std_crash_store.getDump(crash_id)
            with open(job_pathname) as  dump_file:
                binary = dump_file.read()
            return binary
        except OSError:
            raise CrashIDNotFound(crash_id)

    #--------------------------------------------------------------------------
    def new_crashes(self):
        """return an iterator that yields a list of crash_ids of raw crashes
        that were added to the file system since the last time this iterator
        was requested."""
        # why is this called 'destructiveDateWalk'?  The underlying code
        # that manages the filesystem uses a tree of radix date directories
        # and symbolic links to track "new" raw crashes.  As the the crash_ids
        # are fetched from the file system, the symbolic links are removed and
        # directories are deleted.  Essentially, the state of what is
        # considered to be new is saved within the file system by those links.
        return self.std_crash_store.destructiveDateWalk()

    #--------------------------------------------------------------------------
    def remove(self, crash_id):
        """delegate removal of a raw crash to the underlying filesystem"""
        try:
            self.std_crash_store.remove(crash_id)
        except NoSuchUuidFound:
            raise CrashIDNotFound(crash_id)


#==============================================================================
class FileSystemThrottledCrashStorage(FileSystemRawCrashStorage):
    """This varient of file system storage segregates crashes based on
    the result of Collector throttling.  When the collector recieves a crash,
    it applies throttle rules and saves the result in the crash json under the
    key 'legacy_processing'.  Only crashes that have a value of 0 in that field
    will eventually make it on to processing.
        legacy_processing == 0 : crashes stored in the filesystem rooted at
                                 'std_fs_root' (standard file system storage)
                                 defined in the parent class
        legacy_processing == 1 : crashes stored in the filesysetm rooted at
                                 'def_fs_root' (deferred file system storage)
                                 defined in this class
    This class only implements raw crash storage and is not appropriate for
    storing processed crashes."""

    required_config = Namespace()
    required_config.add_option(
        'def_fs_root',
        doc='a path to a local file system',
        default='/home/socorro/deferredCrashStore'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(FileSystemThrottledCrashStorage, self).__init__(config)

        self.def_crash_store = JsonDumpStorage(
          root=config.def_fs_root,
          maxDirectoryEntries=config.dump_dir_count,
          jsonSuffix=config.json_file_suffix,
          dumpSuffix=config.dump_file_suffix,
          dumpGID=config.dump_gid,
          dumpPermissions=config.dump_permissions,
          dirPermissions=config.dir_permissions,
          logger=config.logger
        )
        self.crash_store_iterable = (self.std_crash_store,
                                     self.def_crash_store)

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dump, crash_id):
        """save the raw crash and the dump in the appropriate file system
        based on the value of 'legacy_processing' with the raw_crash itself"""
        try:
            if raw_crash['legacy_processing'] == LegacyThrottler.ACCEPT:
                self._do_save_raw(
                  self.std_crash_store,
                  raw_crash,
                  dump,
                  crash_id
                )
            else:
                self._do_save_raw(
                  self.def_crash_store,
                  raw_crash,
                  dump,
                  crash_id
                )
        except KeyError:
            # if 'legacy_processing' is missing, then it assumed that this
            # crash should be processed.  Therefore save it into standard
            # storage
            self._do_save_raw(self.std_crash_store, raw_crash, dump)

    #--------------------------------------------------------------------------
    def get_raw_crash(self, crash_id):
        """fetch the raw_crash trying each file system in turn"""
        for a_crash_store in self.crash_store_iterable:
            try:
                pathname = a_crash_store.getJson(crash_id)
                return self._load_raw_crash_from_file(pathname)
            except OSError:
                # only raise the exception if we've got no more file systems
                # to look through
                if a_crash_store is self.crash_store_iterable[-1]:
                    raise CrashIDNotFound(crash_id)

    #--------------------------------------------------------------------------
    def get_raw_dump(self, crash_id):
        """fetch the dump trying each file system in turn"""
        for a_crash_store in self.crash_store_iterable:
            try:
                job_pathname = a_crash_store.getDump(crash_id)
                with open(job_pathname) as  dump_file:
                    dump = dump_file.read()
                return dump
            except OSError:
                # only raise the exception if we've got no more file systems
                # to look through
                if a_crash_store is self.crash_store_iterable[-1]:
                    raise CrashIDNotFound(crash_id)

    #--------------------------------------------------------------------------
    def remove(self, crash_id):
        """try to remove the raw_crash and the dump from each  """
        for a_crash_store in self.crash_store_iterable:
            try:
                a_crash_store.remove(crash_id)  # raises NoSuchUuidFound if
                                            # unsuccessful.
                return  # break the loop as soon as we succeed
            except NoSuchUuidFound:
                # only raise the exception if we've got no more file systems
                # to look through
                if a_crash_store is self.crash_store_iterable[-1]:
                    raise CrashIDNotFound(crash_id)


#==============================================================================
class FileSystemCrashStorage(FileSystemThrottledCrashStorage):
    """This storage class is the only file system based crash storage system
    appropriate for storing both raw and processed crashes.  This class uses
    the same segregating raw crash storage as the previous class and adds
    processed storage.  Processed crashes are stored in their own file system
    root, 'pro_fs_root' (processed file system root) using the same radix
    directory system as the raw crashes."""

    required_config = Namespace()
    required_config.add_option(
        'pro_fs_root',
        doc='a path to a local file system for processed storage',
        default='/home/socorro/processedCrashStore'
    )
    required_config.add_option(
        'minutes_per_slot',
        doc='the number of minutes in the lowest date directory',
        default=1
    )
    required_config.add_option(
        'sub_slot_count',
        doc='distribute data evenly among this many sub timeslots',
        default=1
    )
    required_config.add_option(
        'index_name',
        doc='the relative path to the top of the name storage tree from '
            'root parameter',
        default='name'
    )
    required_config.add_option(
        'date_name',
        doc='the relative path to the top of the date storage tree from '
            'root parameter',
        default='date'
    )
    required_config.add_option(
        'processed_crash_file_suffix',
        doc='the processed crash filename suffix',
        default='.jsonz'
    )
    required_config.add_option(
        'gzip_compression_level',
        doc='the level of compression to use',
        default=9
    )
    required_config.add_option(
        'storage_depth',
        doc='the length of branches in the radix storage tree',
        default=2
    )
    required_config.add_option(
        'forbidden_keys',
        doc='a comma delimited list of keys to not allowed in the processed '
            'crash',
        default='url, email, user_id',
        from_string_converter=lambda x: [i.strip() for i in x.split(',')]
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(FileSystemCrashStorage, self).__init__(config)
        self.pro_crash_store = ProcessedDumpStorage(
          root=config.pro_fs_root,
          minutesPerSlot=config.minutes_per_slot,
          subSlotCount=config.sub_slot_count,
          indexName=config.index_name,
          dateName=config.date_name,
          fileSuffix=config.processed_crash_file_suffix,
          gzipCompression=config.gzip_compression_level,
          storageDepth=config.storage_depth,
          dumpGID=config.dump_gid,
          dumpPermissions=config.dump_permissions,
          dirPermissions=config.dir_permissions,
        )

    #--------------------------------------------------------------------------
    def save_processed(self, processed_crash):
        """save a processed crash (in the form of a Mapping) into a json
        file.  It first gets the underlying file system to give it a file
        handle open for writing, then it uses the 'json' module to write
        the mapping to the open file handle."""
        try:
            crash_id = processed_crash['uuid']
        except KeyError:
            raise CrashIDNotFound("uuid missing from processed_crash")
        try:
            processed_crash = self.sanitize_processed_crash(
              processed_crash,
              self.config.forbidden_keys
            )
            self._stringify_dates_in_dict(processed_crash)
            processed_crash_file_handle = \
                self.pro_crash_store.newEntry(crash_id)
            try:
                json.dump(processed_crash, processed_crash_file_handle)
            finally:
                processed_crash_file_handle.close()
            self.logger.debug('saved processed- %s', crash_id)
        except Exception:
            self.logger.critical(
              'processed file system storage has failed for: %s',
              crash_id,
              exc_info=True
            )
            raise

    #--------------------------------------------------------------------------
    def get_processed(self, crash_id):
        """fetch a processed json file from the underlying file system"""
        try:
            return self.pro_crash_store.getDumpFromFile(crash_id)
        except OSError:
            raise CrashIDNotFound(crash_id)

    #--------------------------------------------------------------------------
    def remove(self, crash_id):
        """remove the all traces of a crash, both raw and processed from the
        file system."""
        try:
            super(FileSystemCrashStorage, self).remove(crash_id)
        except CrashIDNotFound:
            self.logger.warning(
              'raw crash not found for deletion: %s',
              crash_id
            )
        try:
            self.pro_crash_store.removeDumpFile(crash_id)
        except OSError:
            self.logger.warning('processed crash not found for deletion: %s',
                                crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def sanitize_processed_crash(processed_crash, forbidden_keys):
        """returns a copy of a processed_crash with the forbidden keys removed.

        parameters:
            processed_crash - the processed crash in the form of a mapping
            forbidden_keys - a list of strings to be removed from the
                             processed crash

        returns:
            a mapping that is a shallow copy of the original processed_crash
            minus the forbidden keys and values"""

        a_copy = processed_crash.copy()
        for a_forbidden_key in forbidden_keys:
            if a_forbidden_key in a_copy:
                del a_copy[a_forbidden_key]
        return a_copy

    #--------------------------------------------------------------------------
    @staticmethod
    def _stringify_dates_in_dict(a_dict):
        for name, value in a_dict.iteritems():
            if isinstance(value, datetime.datetime):
                a_dict[name] = ("%4d-%02d-%02d %02d:%02d:%02d.%d" %
                  (value.year,
                   value.month,
                   value.day,
                   value.hour,
                   value.minute,
                   value.second,
                   value.microsecond)
                )
