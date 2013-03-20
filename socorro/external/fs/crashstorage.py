# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import errno
import datetime
import json
import os
import gzip
import shutil
import stat

from contextlib import contextmanager, closing

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from configman import Namespace
from socorro.external.crashstorage_base import CrashStorageBase, \
                                               CrashIDNotFound
from socorro.lib.ooid import dateFromOoid, depthFromOoid
from socorro.lib.datetimeutil import utc_now
from socorro.lib.util import DotDict

@contextmanager
def using_umask(n):
    old_n = os.umask(n)
    yield
    os.umask(old_n)


class FSRadixTreeStorage(CrashStorageBase):
    """
    This class implements basic radix tree storage. It stores crashes using the
    crash_id radix scheme under ``fs_root``.

    Files are stored in the following scheme::

        root/yyyymmdd/name_branch_base/radix.../crash_id/<files>

    The date is determined using the date suffix of the crash_id, and the
    name_branch_base is given in the configuration options. The radix is
    computed from the crash_id by substringing the UUID in octets to the depth
    given in the crash_id, for instance:

    0bba929f-8721-460c-dead-a43c20071025 is stored in::

        root/20071025/name/0b/ba/92/9f/0bba929f-8721-460c-dead-a43c20071025

    This storage does not implement ``new_crashes``, but is able to store
    processed crashes. Used alone, it is intended to store only processed
    crashes.
    """

    required_config = Namespace()
    required_config.add_option(
        'fs_root',
        doc='a path to a file system',
        default='./crashes',

        # We strip / from the right so we can consistently use os.sep.join
        # instead of os.path.join (which is faster).
        from_string_converter=lambda x: x.rstrip('/')
    )
    required_config.add_option(
        'umask',
        doc='umask to use for new files',
        default=0o022
    )
    required_config.add_option(
        'json_file_suffix',
        doc='the suffix used to identify a json file',
        default='.json'
    )
    required_config.add_option(
        'jsonz_file_suffix',
        doc='the suffix used to identify a gzipped json file',
        default='.jsonz'
    )
    required_config.add_option(
        'dump_file_suffix',
        doc='the suffix used to identify a dump file',
        default='.dump'
    )
    required_config.add_option(
        'dump_field',
        doc='the default dump field',
        default='upload_file_minidump'
    )
    required_config.add_option(
        'forbidden_keys',
        doc='a comma delimited list of keys to not allowed in the processed '
            'crash',
        default='url, email, user_id, exploitability',
        from_string_converter=lambda x: [i.strip() for i in x.split(',')]
    )
    required_config.add_option(
        'name_branch_base',
        doc='the directory base name to use for the named radix tree storage',
        default='name'
    )

    def __init__(self, *args, **kwargs):
        super(FSRadixTreeStorage, self).__init__(*args, **kwargs)
        try:
            with using_umask(self.config.umask):
                os.makedirs(self.config.fs_root)
        except OSError:
            self.logger.info("didn't make directory: %s " %
                self.config.fs_root)

    @staticmethod
    def _cleanup_empty_dirs(base, leaf):
        parts = leaf.split(os.sep)

        while parts:
            cur = os.sep.join([base] + parts)
            parts.pop()

            try:
                os.rmdir(cur)
            except OSError:
                # this directory isn't empty, so we can stop cleanup
                break

    def _get_dump_file_name(self, crash_id, dump_name):
        if dump_name == self.config.dump_field or not dump_name:
            return crash_id + self.config.dump_file_suffix
        else:
            return "%s.%s%s" % (crash_id,
                                dump_name,
                                self.config.dump_file_suffix)

    @staticmethod
    def _get_radix(crash_id):
        return [crash_id[i * 2:(i + 1) * 2]
                for i in range(depthFromOoid(crash_id))]

    def _get_base(self, crash_id):
        date = dateFromOoid(crash_id)
        if not date:
            date = utc_now()
        date_formatted = "%4d%02d%02d" % (date.year, date.month, date.day)
        return [self.config.fs_root, date_formatted]

    def _get_radixed_parent_directory(self, crash_id):
        return os.sep.join(self._get_base(crash_id) +
                           [self.config.name_branch_base] +
                           self._get_radix(crash_id) +
                           [crash_id])

    def _dump_names_from_paths(self, pathnames):
        dump_names = []
        for a_pathname in pathnames:
            base_name = os.path.basename(a_pathname)
            dump_name = base_name[37:-len(self.config.dump_file_suffix)]
            if not dump_name:
                dump_name = self.config.dump_field
            dump_names.append(dump_name)
        return dump_names

    def _save_files(self, crash_id, files):
        parent_dir = self._get_radixed_parent_directory(crash_id)

        with using_umask(self.config.umask):
            try:
                os.makedirs(parent_dir)
            except OSError:
                # probably already created, ignore
                self.logger.info("could not make directory: %s" %
                    self.config.fs_root)

            for fn, contents in files.iteritems():
                with open(os.sep.join([parent_dir, fn]), 'wb') as f:
                    f.write(contents)

    def save_processed(self, processed_crash):
        crash_id = processed_crash['uuid']
        processed_crash = processed_crash.copy()
        f = StringIO()
        for k in self.config.forbidden_keys:
            if k in processed_crash:
                del processed_crash[k]
        with closing(gzip.GzipFile(mode='wb', fileobj=f)) as fz:
            json.dump(processed_crash, fz, default=self.json_default)
        self._save_files(crash_id, {
            crash_id + self.config.jsonz_file_suffix: f.getvalue()
        })

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        files = {
            crash_id + self.config.json_file_suffix: json.dumps(raw_crash)
        }
        files.update(dict((self._get_dump_file_name(crash_id, fn), dump)
                          for fn, dump in dumps.iteritems()))
        self._save_files(crash_id, files)

    def get_raw_crash(self, crash_id):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound
        with open(os.sep.join([parent_dir,
                               crash_id + self.config.json_file_suffix]),
                  'r') as f:
            return json.load(f, object_hook=DotDict)

    def get_raw_dump(self, crash_id, name=None):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound
        with open(os.sep.join([parent_dir,
                               self._get_dump_file_name(crash_id, name)]),
                  'rb') as f:
            return f.read()

    def get_raw_dumps_as_files(self, crash_id):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound
        dump_paths = [os.sep.join([parent_dir, dump_file_name])
                      for dump_file_name in os.listdir(parent_dir)
                      if dump_file_name.startswith(crash_id) and
                         dump_file_name.endswith(self.config.dump_file_suffix)]
        return DotDict(zip(self._dump_names_from_paths(dump_paths),
                           dump_paths))

    def get_raw_dumps(self, crash_id):
        def read_with(fn):
            with open(fn) as f:
                return f.read()
        return DotDict((k, read_with(v))
                       for k, v
                       in self.get_raw_dumps_as_files(crash_id).iteritems())

    def get_processed(self, crash_id):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound
        with closing(gzip.GzipFile(os.sep.join([
                parent_dir,
                crash_id + self.config.jsonz_file_suffix]),
            'rb')) as f:
            return json.load(f, object_hook=DotDict)

    def remove(self, crash_id):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound
        shutil.rmtree(parent_dir)

    @staticmethod
    def json_default(obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S.%f")
        raise TypeError


class FSLegacyRadixTreeStorage(FSRadixTreeStorage):
    """
    The legacy radix tree storage implements a variant of the radix tree
    storage, designed to be backwards-compatible with the old filesystem
    module.

    This filesystem storage does not create a subdirectory with the crash ID
    in the radix tree to store crashes -- instead, it just stores it in the
    final radix part.
    """
    def _get_radixed_parent_directory(self, crash_id):
        return os.sep.join(self._get_base(crash_id) +
                           [self.config.name_branch_base] +
                           self._get_radix(crash_id))


    def remove(self, crash_id):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound

        removal_candidates = [os.sep.join([parent_dir,
                                           crash_id + '.json'])] + \
                             list(self.get_raw_dumps_as_files(crash_id)
                                  .values())

        for cand in removal_candidates:
            try:
                os.unlink(cand)
            except OSError:
                self.config.logger.error("could not delete: %s", cand,
                                         exc_info=True)

class FSDatedRadixTreeStorage(FSRadixTreeStorage):
    """
    This class implements dated radix tree storage -- it enables for traversing
    a radix tree using an hour/minute prefix. It allows searching for new
    crashes, but doesn't store processed crashes.

    It supplements the basic radix tree storage with indexing by date. It takes
    the current hour, minute and second and stores items in the following
    scheme::

        root/yyyymmdd/date_branch_base/hour/minute_(minute_slice)/crash_id

        minute_slice is computed by taking the second of the current timestamp
        and floor dividing by minute_slice_interval, e.g. a minute slice of 4
        provides slots from 0..14.

    This is a symlink to the items stored in the base radix tree storage.
    Additionally, a symlink is created in the base radix tree directory called
    ``date_root` which links to the ``minute_(minute_slice)`` folder.

    This storage class is suitable for use as raw crash storage, as it supports
    the ``new_crashes`` method.
    """

    required_config = Namespace()
    required_config.add_option(
        'date_branch_base',
        doc='the directory base name to use for the dated radix tree storage',
        default='date'
    )
    required_config.add_option(
        'minute_slice_interval',
        doc='how finely to slice minutes into slots, e.g. 4 means every 4 '
            'seconds a new slot will be allocated',
        default=4
    )

    # This is just a constant for len(self._current_slot()).
    SLOT_DEPTH = 2
    DIR_DEPTH = 2

    def _get_date_root_name(self, crash_id):
        return 'date_root'

    def _get_dump_file_name(self, crash_id, dump_name):
        if dump_name == self.config.dump_field or dump_name is None:
            return crash_id + self.config.dump_file_suffix
        else:
            return "%s.%s%s" % (crash_id,
                                dump_name,
                                self.config.dump_file_suffix)

    def _get_dated_parent_directory(self, crash_id, slot):
        return os.sep.join(self._get_base(crash_id) +
                           [self.config.date_branch_base] + slot)

    def _current_slot(self):
        now = utc_now()
        return ["%02d" % now.hour,
                "%02d_%02d" % (now.minute,
                               now.second //
                                   self.config.minute_slice_interval)]

    def _create_name_to_date_symlink(self, crash_id, slot):
        """we traverse the path back up from date/slot... to make a link:
           src:  "name"/radix.../crash_id (or "name"/radix... for legacy mode)
           dest: "date"/slot.../crash_id"""
        radixed_parent_dir = self._get_radixed_parent_directory(crash_id)

        root = os.sep.join([os.path.pardir] * (self.SLOT_DEPTH + 1))
        os.symlink(os.sep.join([root, self.config.name_branch_base] +
                               self._get_radix(crash_id) +
                               [crash_id]),
                   os.sep.join([self._get_dated_parent_directory(crash_id,
                                                                 slot),
                                crash_id]))

    def _create_date_to_name_symlink(self, crash_id, slot):
        """the path is something like name/radix.../crash_id, so what we do is
           add 2 to the directories to go up _dir_depth + len(radix).
           we make a link:
           src:  "date"/slot...
           dest: "name"/radix.../crash_id/date_root_name"""
        radixed_parent_dir = self._get_radixed_parent_directory(crash_id)

        root = os.sep.join([os.path.pardir] *
                           (len(self._get_radix(crash_id)) + self.DIR_DEPTH))
        os.symlink(os.sep.join([root, self.config.date_branch_base] + slot),
                   os.sep.join([radixed_parent_dir,
                                self._get_date_root_name(crash_id)]))

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        super(FSDatedRadixTreeStorage, self).save_raw_crash(raw_crash,
                                                            dumps, crash_id)

        slot = self._current_slot()
        parent_dir = self._get_dated_parent_directory(crash_id, slot)

        try:
            os.makedirs(parent_dir)
        except OSError:
            # probably already created, ignore
            self.logger.info("could not make directory: %s" %
                parent_dir)

        with using_umask(self.config.umask):
            self._create_name_to_date_symlink(crash_id, slot)
            self._create_date_to_name_symlink(crash_id, slot)

    def remove(self, crash_id):
        dated_path = os.path.realpath(
            os.sep.join([self._get_radixed_parent_directory(crash_id),
                         self._get_date_root_name(crash_id)]))

        try:
            # We can just unlink the symlink and later new_crashes will clean
            # up for us.
            os.unlink(os.sep.join([dated_path, crash_id]))
        except OSError:
            pass  # we might be trying to remove a visited crash and that's
                  # okay

        # Now we actually remove the crash.
        super(FSDatedRadixTreeStorage, self).remove(crash_id)

    def _visit_minute_slot(self, minute_slot_base):
        for crash_id in os.listdir(minute_slot_base):
            namedir = os.sep.join([minute_slot_base, crash_id])
            st_result = os.lstat(namedir)

            if stat.S_ISLNK(st_result.st_mode):
                # This is a link, so we can dereference it to find
                # crashes.
                if os.path.isfile(
                    os.sep.join([namedir,
                                 crash_id +
                                 self.config.json_file_suffix])):
                    date_root_path = os.sep.join([
                        namedir,
                        self._get_date_root_name(crash_id)
                    ])
                    yield crash_id

                    try:
                        os.unlink(date_root_path)
                    except OSError as e:
                        self.logger.error("could not find a date root in "
                                          "%s; is crash corrupt?",
                                          namedir,
                                          exc_info=True)

                    os.unlink(namedir)

    def new_crashes(self):
        """
        The ``new_crashes`` method returns a generator that visits all new
        crashes like so:

        * Traverse the date root to find all crashes.

        * If we find a symlink in a slot, then we dereference the link and
          check if the directory has crash data.

        * if the directory does, then we remove the symlink in the slot,
          clean up the parent directories if they're empty and then yield
          the crash_id.
        """
        current_slot = self._current_slot()

        date = utc_now()
        current_date = "%4d%02d%02d" % (date.year, date.month, date.day)

        dates = os.listdir(self.config.fs_root)
        for date in dates:
            dated_base = os.sep.join([self.config.fs_root, date,
                                      self.config.date_branch_base])

            try:
                hour_slots = os.listdir(dated_base)
            except OSError:
                # it is okay that the date root doesn't exist - skip on to
                # the next date
                #self.logger.info("date root for %s doesn't exist" % date)
                continue

            for hour_slot in hour_slots:
                skip_dir = False
                hour_slot_base = os.sep.join([dated_base, hour_slot])
                for minute_slot in os.listdir(hour_slot_base):
                    minute_slot_base = os.sep.join([hour_slot_base,
                                                    minute_slot])
                    slot = [hour_slot, minute_slot]

                    if slot >= current_slot and date >= current_date:
                        # the slot is currently being used, we want to skip it
                        # for now
                        self.logger.info("not processing slot: %s/%s" %
                                         tuple(slot))
                        skip_dir = True
                        continue

                    for x in self._visit_minute_slot(minute_slot_base):
                        yield x

                    try:
                        # We've finished processing the slot, so we can remove
                        # it.
                        os.rmdir(minute_slot_base)
                    except OSError as e:
                        self.logger.error("could not fully remove directory: "
                                          "%s; are there more crashes in it?",
                                          minute_slot_base,
                                          exc_info=True)

                if not skip_dir and hour_slot < current_slot[0]:
                    try:
                        # If the current slot is greater than the hour slot
                        # we're processing, then we can conclude the directory
                        # is safe to remove.
                        os.rmdir(hour_slot_base)
                    except OSError as e:
                       self.logger.error("could not fully remove directory: "
                                          "%s; are there more crashes in it?",
                                          hour_slot_base,
                                          exc_info=True)


class FSLegacyDatedRadixTreeStorage(FSDatedRadixTreeStorage,
                                    FSLegacyRadixTreeStorage):
    """
    This legacy radix tree storage implements a backwards-compatible with the
    old filesystem storage by setting the symlinks up correctly.

    The rationale for creating a diamond structure for multiple inheritance is
    two-fold:

     * The implementation of ``_get_radixed_parent_directory`` is required from
       ``FSLegacyRadixTreeStorage`` and ``FSDatedRadixTreeStorage`` requires
       the behavior of the implementation from ``FSLegacyRadixTreeStorage`` to
       function correctly.

     * The implementation of ``remove`` is also required from
       ``FSDatedRadixTreeStorage``, and the order is dependent as it requires
       the MRO to resolve ``remove`` from the ``FSDatedRadixTreeStorage``
       first, over ``FSLegacyRadixTreeStorage``.
    """
    DIR_DEPTH = 1

    def _get_date_root_name(self, crash_id):
        return crash_id

    def _create_name_to_date_symlink(self, crash_id, slot):
        root = os.sep.join([os.path.pardir] * (self.SLOT_DEPTH + 1))
        os.symlink(os.sep.join([root, self.config.name_branch_base] +
                               self._get_radix(crash_id)),
                   os.sep.join([self._get_dated_parent_directory(crash_id,
                                                                 slot),
                                crash_id]))

    def _visit_minute_slot(self, minute_slot_base):
        for crash_id_or_webhead in os.listdir(minute_slot_base):
            namedir = os.sep.join([minute_slot_base, crash_id_or_webhead])
            st_result = os.lstat(namedir)

            if stat.S_ISLNK(st_result.st_mode):
                crash_id = crash_id_or_webhead

                # This is a link, so we can dereference it to find
                # crashes.
                if os.path.isfile(
                    os.sep.join([namedir,
                                 crash_id +
                                 self.config.json_file_suffix])):
                    date_root_path = os.sep.join([
                        namedir,
                        self._get_date_root_name(crash_id)
                    ])

                    yield crash_id

                    try:
                        os.unlink(date_root_path)
                    except OSError as e:
                        self.logger.error("could not find a date root in "
                                          "%s; is crash corrupt?",
                                          date_root_path,
                                          exc_info=True)

                    os.unlink(namedir)

            elif stat.S_ISDIR(st_result.st_mode):
                webhead_slot = crash_id_or_webhead
                webhead_slot_base = os.sep.join([minute_slot_base,
                                                 webhead_slot])

                # This is actually a webhead slot, but we can visit it as if
                # it was a minute slot.
                for x in self._visit_minute_slot(webhead_slot_base):
                    yield x

                try:
                    os.rmdir(webhead_slot_base)
                except OSError as e:
                    self.logger.error("could not fully remove directory: "
                                      "%s; are there more crashes in it?",
                                      webhead_slot_base,
                                      exc_info=True)
            else:
                self.logger.critical("unknown file %s found", namedir)
