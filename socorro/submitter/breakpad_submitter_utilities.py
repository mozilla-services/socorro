# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/

import os
import urllib2

from configman import Namespace
import poster

from socorro.external.crashstorage_base import CrashStorageBase


poster.streaminghttp.register_openers()


class BreakpadPOSTDestination(CrashStorageBase):
    """This a crashstorage derivative that pushes a crash out to a Socorro collector waiting at a url.

    """
    required_config = Namespace()
    required_config.add_option(
        'urls',
        doc='One or more urls to submit to separated by commas',
        default="http://127.0.0.1:8888/submit"
    )

    def save_raw_crash_with_file_dumps(self, raw_crash, dumps, crash_id):
        """Saves a raw crash by wrapping it up in a multipart/form-data payload and submitting it as an HTTP
        POST to a collector

        """
        urls = self.config.urls.split(',')

        try:
            # Create raw crash with file pointers to minidumps for poster to pull from
            for dump_name, dump_pathname in dumps.iteritems():
                if not dump_name:
                    dump_name = self.config.source.dump_field
                raw_crash[dump_name] = open(dump_pathname, 'rb')

            # Get uuid for logging purposes
            uuid = raw_crash.get('uuid', 'NO UUID')

            # Build the payload
            datagen, headers = poster.encode.multipart_encode(raw_crash)

            # Submit payload to all urls
            for url in urls:
                request = urllib2.Request(url, datagen, headers)
                submission_response = urllib2.urlopen(request).read().strip()
                self.config.logger.debug(
                    'submitted %s to %s; response %s', uuid, url, submission_response
                )

        finally:
            for dump_name, dump_pathname in dumps.iteritems():
                if "TEMPORARY" in dump_pathname:
                    os.unlink(dump_pathname)
