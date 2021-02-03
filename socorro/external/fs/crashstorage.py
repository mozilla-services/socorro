# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from contextlib import contextmanager, closing
import gzip
import json
from io import BytesIO
import os

from configman import Namespace
from configman.dotdict import DotDict

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound,
    FileDumpsMapping,
    MemoryDumpsMapping,
)
from socorro.lib.datetimeutil import utc_now, JsonDTISOEncoder
from socorro.lib.ooid import date_from_ooid, depth_from_ooid


@contextmanager
def using_umask(n):
    old_n = os.umask(n)
    yield
    os.umask(old_n)


class FSPermanentStorage(CrashStorageBase):
    """File-system crash storage

    This class implements basic radix tree storage. It stores crashes using the
    ``crash_id`` radix scheme under ``fs_root``.

    Files are stored in the following scheme::

        root/yyyymmdd/name_branch_base/radix.../<files>

    The depth of directory is specified by the seventh directory from the
    right, i.e. the first 0 in 2009 in the example. By default, if the value is
    0, the nesting is 4.

    The leaf directory contains the raw crash information, exported as JSON,
    and the various associated dump files -- or, if being used as processed
    storage, contains the processed JSON file.

    The date is determined using the date suffix of the crash_id, and the
    name_branch_base is given in the configuration options. The radix is
    computed from the crash_id by substringing the UUID in octets to the depth
    given in the crash_id, for instance:

    0bba929f-8721-460c-dead-a43c20071025 is stored in::

        root/20071025/name/0b/ba/92/9f/

    Used alone, it is intended to store only processed crashes.

    """

    required_config = Namespace()
    required_config.add_option(
        "fs_root",
        doc="a path to a file system",
        default="./crashes",
        # We strip / from the right so we can consistently use os.sep.join
        # instead of os.path.join (which is faster).
        from_string_converter=lambda x: x.rstrip("/"),
        reference_value_from="resource.fs",
    )
    required_config.add_option(
        "umask",
        doc="umask to use for new files",
        default=0o022,
        reference_value_from="resource.fs",
    )
    required_config.add_option(
        "json_file_suffix",
        doc="the suffix used to identify a json file",
        default=".json",
        reference_value_from="resource.fs",
    )
    required_config.add_option(
        "jsonz_file_suffix",
        doc="the suffix used to identify a gzipped json file",
        default=".jsonz",
        reference_value_from="resource.fs",
    )
    required_config.add_option(
        "dump_file_suffix",
        doc="the suffix used to identify a dump file",
        default=".dump",
        reference_value_from="resource.fs",
    )
    required_config.add_option(
        "dump_field",
        doc="the default dump field",
        default="upload_file_minidump",
        reference_value_from="resource.fs",
    )
    required_config.add_option(
        "name_branch_base",
        doc="the directory base name to use for the named radix tree storage",
        default="name",
        reference_value_from="resource.fs",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            with using_umask(self.config.umask):
                os.makedirs(self.config.fs_root)
        except OSError:
            self.logger.info("didn't make directory: %s " % self.config.fs_root)

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
            return "%s.%s%s" % (crash_id, dump_name, self.config.dump_file_suffix)

    @staticmethod
    def _get_radix(crash_id):
        return [crash_id[i * 2 : (i + 1) * 2] for i in range(depth_from_ooid(crash_id))]

    def _get_base(self, crash_id):
        date = date_from_ooid(crash_id)
        if not date:
            date = utc_now()
        date_formatted = "%4d%02d%02d" % (date.year, date.month, date.day)
        return [self.config.fs_root, date_formatted]

    def _dump_names_from_paths(self, pathnames):
        dump_names = []
        for a_pathname in pathnames:
            base_name = os.path.basename(a_pathname)
            dump_name = base_name[37 : -len(self.config.dump_file_suffix)]
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
                pass

            for fn, contents in files.items():
                with open(os.sep.join([parent_dir, fn]), "wb") as f:
                    f.write(contents)

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        if dumps is None:
            dumps = MemoryDumpsMapping()
        files = {
            crash_id
            + self.config.json_file_suffix: json.dumps(raw_crash).encode("utf-8")
        }
        in_memory_dumps = dumps.as_memory_dumps_mapping()
        files.update(
            {
                self._get_dump_file_name(crash_id, fn): dump
                for fn, dump in in_memory_dumps.items()
            }
        )
        self._save_files(crash_id, files)

    def save_processed_crash(self, raw_crash, processed_crash):
        crash_id = processed_crash["uuid"]
        processed_crash = processed_crash.copy()
        f = BytesIO()
        with closing(gzip.GzipFile(mode="wb", fileobj=f)) as fz:
            data = json.dumps(processed_crash, cls=JsonDTISOEncoder)
            fz.write(data.encode("utf-8"))
        self._save_files(
            crash_id, {crash_id + self.config.jsonz_file_suffix: f.getvalue()}
        )

    def get_raw_crash(self, crash_id):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound
        with open(
            os.sep.join([parent_dir, crash_id + self.config.json_file_suffix])
        ) as f:
            return json.load(f, object_hook=DotDict)

    def get_raw_dump(self, crash_id, name=None):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound
        with open(
            os.sep.join([parent_dir, self._get_dump_file_name(crash_id, name)]), "rb"
        ) as f:
            return f.read()

    def get_raw_dumps_as_files(self, crash_id):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound
        dump_paths = [
            os.sep.join([parent_dir, dump_file_name])
            for dump_file_name in os.listdir(parent_dir)
            if (
                dump_file_name.startswith(crash_id)
                and dump_file_name.endswith(self.config.dump_file_suffix)
            )
        ]
        # we want to return a name/pathname mapping for the raw dumps
        return FileDumpsMapping(
            zip(self._dump_names_from_paths(dump_paths), dump_paths)
        )

    def get_raw_dumps(self, crash_id):
        file_dump_mapping = self.get_raw_dumps_as_files(crash_id)
        # ensure that we return a name/blob mapping
        return file_dump_mapping.as_memory_dumps_mapping()

    def get_unredacted_processed(self, crash_id):
        """this method returns an unredacted processed crash"""
        parent_dir = self._get_radixed_parent_directory(crash_id)
        pathname = os.sep.join([parent_dir, crash_id + self.config.jsonz_file_suffix])
        if not os.path.exists(pathname):
            raise CrashIDNotFound
        with closing(gzip.GzipFile(pathname, "rb")) as f:
            return json.load(f, object_hook=DotDict)

    def _get_radixed_parent_directory(self, crash_id):
        return os.sep.join(
            self._get_base(crash_id)
            + [self.config.name_branch_base]
            + self._get_radix(crash_id)
        )

    def remove(self, crash_id):
        parent_dir = self._get_radixed_parent_directory(crash_id)
        if not os.path.exists(parent_dir):
            raise CrashIDNotFound

        removal_candidates = [os.sep.join([parent_dir, crash_id + ".json"])] + list(
            self.get_raw_dumps_as_files(crash_id).values()
        )

        # Remove all the files related to the crash
        for cand in removal_candidates:
            try:
                os.unlink(cand)
            except OSError:
                self.logger.error("could not delete: %s", cand, exc_info=True)

        # If the directory is empty, clean it up
        if len(os.listdir(parent_dir)) == 0:
            try:
                os.rmdir(parent_dir)
            except OSError:
                self.logger.error("could not delete: %s", parent_dir, exc_info=True)
