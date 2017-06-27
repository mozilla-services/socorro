#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""This app will submit crashes to a socorro collector"""


import time
import json

from os import (
    path,
    listdir
)

from configman import Namespace

from socorro.app.fetch_transform_save_app import (
    FetchTransformSaveWithSeparateNewCrashSourceApp,
    main
)
from socorro.external.crashstorage_base import (
    CrashStorageBase,
    FileDumpsMapping,
)
from socorro.external.fs.filesystem import findFileGenerator
from socorro.lib.util import DotDict


class SubmitterFileSystemWalkerSource(CrashStorageBase):
    """This is a crashstorage derivative that can walk an arbitrary file
    system path looking for crashes.  The new_crashes generator yields
    pathnames rather than crash_ids - so it is not compatible with other
    instances of the CrashStorageSystem.

    """
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

    def __init__(self, config, quit_check_callback=None):
        if isinstance(quit_check_callback, basestring):
            # this class is being used as a 'new_crash_source' and the name
            # of the app has been passed - we can ignore it
            quit_check_callback = None
        super(SubmitterFileSystemWalkerSource, self).__init__(
            config,
            quit_check_callback
        )

    def get_raw_crash(self, (prefix, path_tuple)):
        """default implemntation of fetching a raw_crash

        parameters:
           path_tuple - a tuple of paths. the first element is the raw_crash
                        pathname

        """
        with open(path_tuple[0]) as raw_crash_fp:
            return DotDict(json.load(raw_crash_fp))

    def get_unredacted_processed(self, (prefix, path_tuple)):
        """default implemntation of fetching a processed_crash

        parameters:
           path_tuple - a tuple of paths. the first element is the raw_crash
                        pathname

        """
        with open(path_tuple[0]) as processed_crash_fp:
            return DotDict(json.load(processed_crash_fp))

    def get_raw_dumps(self, prefix_path_tuple):
        file_dumps_mapping = self.get_raw_dumps_as_files(prefix_path_tuple)
        return file_dumps_mapping.as_memory_dumps_mapping()

    def get_raw_dumps_as_files(self, prefix_path_tuple):
        """default implemntation of fetching a dump.

        parameters:
           dump_pathnames - a tuple of paths. the second element and beyond are
                            the dump pathnames

        """
        prefix, dump_pathnames = prefix_path_tuple
        return FileDumpsMapping(
            zip(
                self._dump_names_from_pathnames(dump_pathnames[1:]),
                dump_pathnames[1:]
            )
        )

    def _dump_names_from_pathnames(self, pathnames):
        """Given a list of pathnames of this form::

            (uuid[.name].dump)+

        This function will return a list of just the name part of the path.
        in the case where there is no name, it will use the default dump
        name from configuration.

        example::

            ['6611a662-e70f-4ba5-a397-69a3a2121129.dump',
             '6611a662-e70f-4ba5-a397-69a3a2121129.flash1.dump',
             '6611a662-e70f-4ba5-a397-69a3a2121129.flash2.dump',
            ]

        returns::

            ['upload_file_minidump', 'flash1', 'flash2']

        """
        prefix = path.commonprefix([path.basename(x) for x in pathnames])
        prefix_length = len(prefix)
        dump_names = []
        for a_pathname in pathnames:
            base_name = path.basename(a_pathname)
            dump_name = base_name[prefix_length:-len(self.config.dump_suffix)]
            if not dump_name:
                dump_name = self.config.dump_field
            dump_names.append(dump_name)
        return dump_names

    def new_crashes(self):
        # loop over all files under the search_root that have a suffix of
        # ".json"
        for a_path, a_file_name, raw_crash_pathname in findFileGenerator(
            self.config.search_root,
            lambda x: x[2].endswith(".json")
        ):
            prefix = path.splitext(a_file_name)[0]
            crash_pathnames = [raw_crash_pathname]
            for dumpfilename in listdir(a_path):
                if (dumpfilename.startswith(prefix) and
                    dumpfilename.endswith(self.config.dump_suffix)):
                    crash_pathnames.append(
                        path.join(a_path, dumpfilename)
                    )
            # yield the pathnames of all the crash parts - normally, this
            # method in a crashstorage class yields just a crash_id.  In this
            # case however, we have only pathnames to work with. So we return
            # this (args, kwargs) form instead
            yield (((prefix, crash_pathnames), ), {})


# this class was relocated to a more appropriate module and given a new name.
# This import is offered for backwards compatibilty.  Note, that there has also
# been an internal change to the required config, with the source
# implementation moved into a namespace
from socorro.external.postgresql.new_crash_source import (
    DBCrashStorageWrapperNewCrashSource as DBSamplingCrashSource
)


class SubmitterApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    app_name = 'submitter_app'
    app_version = '3.1'
    app_description = __doc__

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

    @staticmethod
    def get_application_defaults():
        return {
            "source.crashstorage_class": SubmitterFileSystemWalkerSource,
            "destination.crashstorage_class": (
                'socorro.submitter.breakpad_submitter_utilities.BreakpadPOSTDestination'
            ),
            "number_of_submissions": "all",
        }

    def _action_between_each_iteration(self):
        if self.config.submitter.delay:
            time.sleep(self.config.submitter.delay)

    def _action_after_iteration_completes(self):
        self.config.logger.info(
            'the queuing iterator is exhausted - waiting to quit'
        )
        self.task_manager.wait_for_empty_queue(
            5,
            "waiting for the queue to drain before quitting"
        )
        time.sleep(self.config.producer_consumer.number_of_threads * 2)

    def _filter_disallowed_values(self, current_value):
        """In this base class there are no disallowed values coming from the
        iterators.  Other users of these iterator may have some standards and
        can detect and reject them here

        """
        return current_value is None

    def _transform(self, crash_id):
        """Transfers raw data from the source to the destination without changing the data

        """
        if self.config.submitter.dry_run:
            print crash_id
        else:
            raw_crash = self.source.get_raw_crash(crash_id)
            dumps = self.source.get_raw_dumps_as_files(crash_id)
            self.destination.save_raw_crash_with_file_dumps(
                raw_crash,
                dumps,
                crash_id
            )


if __name__ == '__main__':
    main(SubmitterApp)
