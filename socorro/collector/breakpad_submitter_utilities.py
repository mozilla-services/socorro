#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/
from configman import Namespace
from socorro.external.crashstorage_base import CrashStorageBase

import os
import urllib2
import poster
poster.streaminghttp.register_openers()


#==============================================================================
class BreakpadPOSTDestination(CrashStorageBase):
    """this a crashstorage derivative that just pushes a crash out to a
    Socorro collector waiting at a url"""
    required_config = Namespace()
    required_config.add_option(
        'url',
        short_form='u',
        doc="The url of the Socorro collector to submit to",
        default="http://127.0.0.1:8882/submit"
    )
    required_config.add_option(
        'echo_response',
        short_form='e',
        doc="echo the submission response to stdout",
        default=False
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(BreakpadPOSTDestination, self).__init__(
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
            submission_response = urllib2.urlopen(request).read().strip()
            try:
                self.config.logger.debug(
                    'submitted %s (original crash_id)',
                    raw_crash['uuid']
                )
            except KeyError:
                pass
            self.config.logger.debug(
                'submission response: %s',
                submission_response
                )
            if self.config.echo_response:
                print submission_response
        finally:
            for dump_name, dump_pathname in dumps.iteritems():
                if "TEMPORARY" in dump_pathname:
                    os.unlink(dump_pathname)

