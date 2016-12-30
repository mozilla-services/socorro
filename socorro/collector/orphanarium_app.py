#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""this app will lists bad """


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
class PlaceholdingDummyClass(CrashStorageBase):
    """this a crashstorage derivative that just pushes a crash out to a
    Socorro collector waiting at a url"""
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(PlaceholdingDummyClass, self).__init__(
            config,
            quit_check_callback
        )



#==============================================================================
class OrphanariumFileSystemWalkerSource(CrashStorageBase):
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
    required_config.namespace('a')
    required_config.a.add_option(
      'crashstorage_class',
      doc='the source storage class',
      default='socorro.external.hbase.crashstorage.HBaseCrashStorage',
      from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(OrphanariumFileSystemWalkerSource, self).__init__(
            config,
            quit_check_callback
        )
        self.crash_store = config.a.crashstorage_class(config.a)  # hbase

    #--------------------------------------------------------------------------
    def new_crashes(self):
        # loop over all files under the search_root that have a suffix of
        # ".dump" llooking for dump orphans in hbase.
        paths_tested = set()
        seen = set()
        for a_path, a_file_name, dump_pathname in findFileGenerator(
            self.config.search_root,
            acceptanceFunction=lambda x: x[2].endswith(".dump"),
            directoryAcceptanceFunction=(lambda x: len(x[2]) <= 51 and
                                         'date' not in x[2]),
        ):
            try:
                self.quit_check()
            except AttributeError:
                pass
            if a_path not in paths_tested:
                self.config.logger.debug('testing %s', a_path)
                paths_tested.add(a_path)
            crash_id = a_file_name.split('.')[0]
            if crash_id in seen:
                continue
            dont_skip = True
            seen.add(crash_id)
            dump_names = ['upload_file_minidump']
            for dumpfilename in os.listdir(a_path):
                if (dumpfilename.startswith(crash_id) and
                    dumpfilename.endswith('json')):
                    dont_skip = False
                    break
                if (dumpfilename.startswith(crash_id) and
                    dumpfilename.endswith('dump')):
                    name_parts = dumpfilename.split('.')
                    if len(name_parts) == 2:
                        continue
                    dump_names.append(name_parts[1])
            if dont_skip:
                stored_dump_names = \
                    self.crash_store.get_raw_dumps(crash_id).keys()
                if sorted(stored_dump_names) == sorted(dump_names):
                    print "# delete duped orphans for", crash_id
                    filenames = [os.path.join(
                                    a_path,
                                    "%s.%s.dump" % (crash_id, x)
                                 )
                                for x in dump_names[1:]]
                    for filename in filenames:
                        print 'rm', filename
                else:
                    print "# fixup", crash_id, dump_names
                yield crash_id

#==============================================================================
class OrphanariumApp(FetchTransformSaveApp):
    app_name = 'orphanarium'
    app_version = '1.0'
    app_description = __doc__

    # set the Option defaults in the parent class to values that make sense
    # for the context of this app
    FetchTransformSaveApp.required_config.source.crashstorage_class. \
        set_default(
            OrphanariumFileSystemWalkerSource,
            force=True,
        )
    FetchTransformSaveApp.required_config.destination.crashstorage_class \
        .set_default(
            PlaceholdingDummyClass,
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

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(OrphanariumApp, self).__init__(config)
        self._crash_set_iter = self._all_iterator


    #--------------------------------------------------------------------------
    def transform(self, crash_id):
        """this transform function only transfers raw data from the
        source to the destination without changing the data."""
        if self.config.submitter.dry_run:
            print crash_id
        else:
            pass

    #--------------------------------------------------------------------------
    def source_iterator(self):
        """this iterator yields pathname pairs for raw crashes and raw dumps"""
        self.source.quit_check = self.quit_check
        for x in self._crash_set_iter():
            if x is None:
                break
            yield ((x,), {})
        self.config.logger.info(
            'the queuing iterator is exhausted - waiting to quit'
        )
        self.task_manager.wait_for_empty_queue(
            5,
            "waiting for the queue to drain before quitting"
        )
        time.sleep(self.config.producer_consumer.number_of_threads * 2)

    #--------------------------------------------------------------------------
    def _all_iterator(self):
        for crash_id in self.source.new_crashes():
            yield crash_id



if __name__ == '__main__':
    main(OrphanariumApp)
