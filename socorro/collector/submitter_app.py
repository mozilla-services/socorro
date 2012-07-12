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

from configman import Namespace

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp, main
from socorro.external.crashstorage_base import CrashStorageBase
from socorro.lib.filesystem import findFileGenerator
from socorro.lib.util import DotDict

poster.streaminghttp.register_openers()


#==============================================================================
class CrashStorageSubmitter(CrashStorageBase):
    required_config = Namespace()
    required_config.add_option(
      'url',
      short_form='u',
      doc="The url of the Socorro collector to submit to",
      default="http://127.0.0.1:8882/submit"
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(CrashStorageSubmitter, self).__init__(
          config,
          quit_check_callback
        )
        self.hang_id_cache = dict()

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dump, crash_id):
        if self.config.submitter.dry_run:
            print raw_crash.ProductName, raw_crash.Version
        else:
            raw_crash['upload_file_minidump'] = open(dump, 'rb')
            datagen, headers = poster.encode.multipart_encode(raw_crash)
            request = urllib2.Request(
              self.config.url,
              datagen,
              headers
            )
            print urllib2.urlopen(request).read(),
            try:
                self.config.logger.debug('submitted %s', raw_crash['uuid'])
            except KeyError:
                self.config.logger.debug('submitted crash with unknown uuid')


#==============================================================================
class SubmitterCrashReader(CrashStorageBase):
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(SubmitterCrashReader, self).__init__(
          config,
          quit_check_callback
        )
        #self.hang_id_cache = dict()

    #--------------------------------------------------------------------------
    def get_raw_crash(self, path_tuple):
        """the default implemntation of fetching a raw_crash

        parameters:
           path_tuple - a tuple of paths. the first element is the raw_crash
                        pathname"""
        with open(path_tuple[0]) as raw_crash_fp:
            return DotDict(json.load(raw_crash_fp))

    #--------------------------------------------------------------------------
    def get_dump(self, path_tuple):
        """the default implemntation of fetching a dump

        parameters:
        path_tuple - a tuple of paths. the second element is the dump
                     pathname"""
        return path_tuple[1]


#==============================================================================
class SubmitterApp(FetchTransformSaveApp):
    app_name = 'submitter_app'
    app_version = '3.0'
    app_description = __doc__

    # set the Option defaults in the parent class to values that make sense
    # for the context of this app
    FetchTransformSaveApp.required_config.source.crashstorage.set_default(
      SubmitterCrashReader
    )
    FetchTransformSaveApp.required_config.destination.crashstorage.set_default(
      CrashStorageSubmitter
    )

    required_config = Namespace()
    required_config.namespace('submitter')
    required_config.submitter.add_option(
      'delay',
      doc="pause between submission queing in milliseconds",
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
    required_config.submitter.add_option(
      'raw_crash',
      doc="the pathname of a raw crash json file to submit",
      short_form='j',
      default=None
    )
    required_config.submitter.add_option(
      'raw_dump',
      doc="the pathname of a dumpfile to submit",
      short_form='d',
      default=None
    )
    required_config.submitter.add_option(
      'search_root',
      doc="a filesystem location to begin a search for raw crash / dump pairs",
      short_form='s',
      default=None
    )
    #required_config.submitter.add_option(
      #'unique_hang_id',
      #doc="cache and uniquify hangids",
      #default=True
    #)

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(SubmitterApp, self).__init__(config)
        if config.submitter.number_of_submissions == 'forever':
            self._crash_pair_iter = \
              self._create_infinite_file_system_iterator()
        elif config.submitter.number_of_submissions == 'all':
            self._crash_pair_iter = self._create_file_system_iterator()
        else:
            self._crash_pair_iter = self._create_limited_file_system_iterator()
            self.number_of_submissions = int(
              config.submitter.number_of_submissions
            )

    #--------------------------------------------------------------------------
    def source_iterator(self):
        """this iterator yields pathname pairs for raw crashes and raw dumps"""
        for x in self._crash_pair_iter():
            yield ((x,), {})  # (raw_crash_pathname, raw_dump_pathname)

    #--------------------------------------------------------------------------
    def _create_file_system_iterator(self):
        def an_iter():
            for a_path, a_file_name, raw_crash_pathname in findFileGenerator(
              self.config.submitter.search_root,
              lambda x: x[2].endswith("json")
            ):
                dumpfilePathName = os.path.join(
                  a_path,
                  "%s%s" % (a_file_name[:-5], ".dump")
                )
                yield (raw_crash_pathname, dumpfilePathName)
                if self.config.submitter.delay:
                    time.sleep(self.config.submitter.delay)
        return an_iter

    #--------------------------------------------------------------------------
    def _create_infinite_file_system_iterator(self):
        an_iterator = self._create_file_system_iterator()

        def infinite_iterator():
            while True:
                for x in an_iterator():
                    yield x
        return infinite_iterator

    #--------------------------------------------------------------------------
    def _create_limited_file_system_iterator(self):
        an_iterator = self._create_infinite_file_system_iterator()

        def limited_iterator():
            for i, x in enumerate(an_iterator()):
                if i >= self.number_of_submissions:
                    break
                yield x
        return limited_iterator


if __name__ == '__main__':
    main(SubmitterApp)
