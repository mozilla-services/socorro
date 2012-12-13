#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""this app will submit crashes to a socorro collector"""


import poster
import time
import os.path
import json
import urllib2

from configman import Namespace, RequiredConfig
from configman.converters import class_converter

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp, main
from socorro.external.crashstorage_base import CrashStorageBase
from socorro.external.filesystem.filesystem import findFileGenerator
from socorro.lib.util import DotDict
from socorro.external.postgresql.dbapi2_util import execute_query_iter

poster.streaminghttp.register_openers()


#==============================================================================
class SubmitterCrashStorageDestination(CrashStorageBase):
    """this a crashstorage derivative that just pushes a crash out to a
    Socorro collector waiting at a url"""
    required_config = Namespace()
    required_config.add_option(
        'url',
        short_form='u',
        doc="The url of the Socorro collector to submit to",
        default="http://127.0.0.1:8882/submit"
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(SubmitterCrashStorageDestination, self).__init__(
            config,
            quit_check_callback
        )
        self.hang_id_cache = dict()

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        try:
            for dump_name, dump_pathname in dumps.iteritems():
                if not dump_name:
                    dump_name = self.config.source.dump_field
                raw_crash[dump_name] = open(dump_pathname, 'rb')
            datagen, headers = poster.encode.multipart_encode(raw_crash)
            request = urllib2.Request(
                self.config.url,
                datagen,
                headers
            )
            print urllib2.urlopen(request).read(),
            try:
                self.config.logger.debug('submitted %s (original crash_id)',
                                         raw_crash['uuid'])
            except KeyError:
                self.config.logger.debug('submitted crash')
        finally:
            for dump_name, dump_pathname in dumps.iteritems():
                if "TEMPORARY" in dump_pathname:
                    os.unlink(dump_pathname)


#==============================================================================
class SubmitterFileSystemWalkerSource(CrashStorageBase):
    """This is a crashstorage derivative that can walk an arbitrary file
    system path looking for crashes.  The new_crashes generator yields
    pathnames rather than crash_ids - so it is not compatible with other
    instances of the CrashStorageSystem."""
    required_config = Namespace()
    required_config.add_option(
        'search_root',
        doc="a filesystem location to begin a search for raw crash/dump sets",
        short_form='s',
        default=None
    )
    required_config.add_option(
        'dump_suffix',
        doc="the standard file extension for dumps",
        default='.dump'
    )
    required_config.add_option(
        'dump_field',
        doc="the default name for the main dump",
        default='upload_file_minidump'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(SubmitterFileSystemWalkerSource, self).__init__(
            config,
            quit_check_callback
        )

    #--------------------------------------------------------------------------
    def get_raw_crash(self, path_tuple):
        """the default implemntation of fetching a raw_crash
        parameters:
           path_tuple - a tuple of paths. the first element is the raw_crash
                        pathname"""
        with open(path_tuple[0]) as raw_crash_fp:
            return DotDict(json.load(raw_crash_fp))

    #--------------------------------------------------------------------------
    def get_raw_dumps_as_files(self, dump_pathnames):
        """the default implemntation of fetching a dump.
        parameters:
        dump_pathnames - a tuple of paths. the second element and beyond are
                         the dump pathnames"""
        # TODO: read the dumps not just echo the paths
        return dict(zip(self._dump_names_from_pathnames(dump_pathnames[1:]),
                        dump_pathnames[1:]))

    #--------------------------------------------------------------------------
    def _dump_names_from_pathnames(self, pathnames):
        """Given a list of pathnames of this form:

        (uuid[.name].dump)+

        This function will return a list of just the name part of the path.
        in the case where there is no name, it will use the default dump
        name from configuration.

        example:

        ['6611a662-e70f-4ba5-a397-69a3a2121129.dump',
         '6611a662-e70f-4ba5-a397-69a3a2121129.flash1.dump',
         '6611a662-e70f-4ba5-a397-69a3a2121129.flash2.dump',
        ]

        returns

        ['upload_file_minidump', 'flash1', 'flash2']
        """
        prefix = os.path.commonprefix([os.path.basename(x) for x in pathnames])
        prefix_length = len(prefix)
        dump_names = []
        for a_pathname in pathnames:
            base_name = os.path.basename(a_pathname)
            dump_name = base_name[prefix_length:-len(self.config.dump_suffix)]
            if not dump_name:
                dump_name = self.config.dump_field
            dump_names.append(dump_name)
        return dump_names

    #--------------------------------------------------------------------------
    def new_crashes(self):
        while True:
            # loop over all files under the search_root that have a suffix of
            # ".json"
            for a_path, a_file_name, raw_crash_pathname in findFileGenerator(
                self.config.search_root,
                lambda x: x[2].endswith(".json")
            ):
                prefix = os.path.splitext(a_file_name)[0]
                crash_pathnames = [raw_crash_pathname]
                for dumpfilename in os.listdir(a_path):
                    if (dumpfilename.startswith(prefix) and
                        dumpfilename.endswith(self.config.dump_suffix)):
                        crash_pathnames.append(os.path.join(a_path,
                                                            dumpfilename))
                # yield the pathnames of all the crash parts
                yield crash_pathnames


#==============================================================================
class SamplingCrashStorageSource(RequiredConfig):
    """this class will take a random sample of crashes in the jobs table
    and then pull them from whatever primary storages is in use. """

    required_config = Namespace()
    required_config.add_option(
        'source_implementation',
        default='socorro.external.hbase.crashstorage.HBaseCrashStorage',
        doc='a class for a source of raw crashes',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'database_class',
        default='socorro.external.postgresql.connection_context'
                '.ConnectionContext',
        doc='the class that connects to the database',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'sql',
        default='select uuid from jobs order by queueddatetime DESC '
                'limit 1000',
        doc='an sql string that selects crash_ids',
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        self._implementation = config.source_implementation(
            config,
            quit_check_callback
        )
        self.config = config
        self.quit_check = quit_check_callback

    #--------------------------------------------------------------------------
    def new_crashes(self):
        while True:
            with self.config.database_class(self.config)() as conn:
                self.quit_check()
                for a_crash_id in execute_query_iter(conn, self.config.sql):
                    self.quit_check()
                    yield a_crash_id[0]
                else:
                    yield None

    #--------------------------------------------------------------------------
    def get_raw_crash(self, crash_id):
        """forward the request to the underlying implementation"""
        return self._implementation.get_raw_crash(crash_id)

    #--------------------------------------------------------------------------
    def get_raw_dumps_as_files(self, crash_id):
        """forward the request to the underlying implementation"""
        return self._implementation.get_raw_dumps_as_files(crash_id)


#==============================================================================
class SubmitterApp(FetchTransformSaveApp):
    app_name = 'submitter_app'
    app_version = '3.1'
    app_description = __doc__

    # set the Option defaults in the parent class to values that make sense
    # for the context of this app
    FetchTransformSaveApp.required_config.source.crashstorage_class. \
        set_default(
            SubmitterFileSystemWalkerSource,
            force=True,
        )
    FetchTransformSaveApp.required_config.destination.crashstorage_class \
        .set_default(
            SubmitterCrashStorageDestination,
            force=True,
        )

    required_config = Namespace()
    required_config.namespace('submitter')
    required_config.submitter.add_option(
        'delay',
        doc="pause between submission queuing in milliseconds",
        default='0',
        from_string_converter=lambda x: float(x) / 1000.0
    )
    required_config.submitter.add_option(
        'dry_run',
        doc="don't actually submit, just print product/version from raw crash",
        short_form='D',
        default=False
    )
    required_config.submitter.add_option(
        'number_of_submissions',
        doc="the number of crashes to submit (all, forever, 1...)",
        short_form='n',
        default='all'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(SubmitterApp, self).__init__(config)
        if config.submitter.number_of_submissions == 'forever':
            self._crash_set_iter = self._infinite_iterator
        elif config.submitter.number_of_submissions == 'all':
            self._crash_set_iter = self._all_iterator
        else:
            self._crash_set_iter = self._limited_iterator

    #--------------------------------------------------------------------------
    def transform(self, crash_id):
        """this transform function only transfers raw data from the
        source to the destination without changing the data."""
        if self.config.submitter.dry_run:
            print crash_id
        else:
            raw_crash = self.source.get_raw_crash(crash_id)
            dumps = self.source.get_raw_dumps_as_files(crash_id)
            self.destination.save_raw_crash(raw_crash, dumps, crash_id)

    #--------------------------------------------------------------------------
    def source_iterator(self):
        """this iterator yields pathname pairs for raw crashes and raw dumps"""
        for x in self._crash_set_iter():
            yield ((x,), {})  # (raw_crash_pathname, raw_dump_pathname0, ...)
            if self.config.submitter.delay:
                time.sleep(self.config.submitter.delay)

    #--------------------------------------------------------------------------
    def _infinite_iterator(self):
        while True:
            for crash_id in self.source.new_crashes():
                yield crash_id

    #--------------------------------------------------------------------------
    def _all_iterator(self):
        for crash_id in self.source.new_crashes():
            yield crash_id

    #--------------------------------------------------------------------------
    def _limited_iterator(self):
        for i, crash_id in enumerate(self.source.new_crashes()):
            if i == int(self.config.submitter.number_of_submissions):
                break
            yield crash_id


if __name__ == '__main__':
    main(SubmitterApp)
