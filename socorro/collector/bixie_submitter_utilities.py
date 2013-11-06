#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace

from socorro.external.crashstorage_base import CrashStorageBase

import urllib2
import urllib
import json

from os.path import join


#==============================================================================
class BixieGETDestination(CrashStorageBase):
    """this as a crashstorage derivative that pushes Bixie crashes to a
    Bixie collector using HTTP GET"""

    required_config = Namespace()
    required_config.add_option(
        'url',
        short_form='u',
        doc="The url of the Bixie collector to submit to",
        default="http://127.0.0.1:8882/"
    )
    required_config.add_option(
        'echo_response',
        short_form='e',
        doc="echo the submission response to stdout",
        default=False
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(BixieGETDestination, self).__init__(
            config,
            quit_check_callback
        )

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """while the api allows dumps to be passed in, this class is not
        capable of actually transmitting them."""

        crash_to_submit = {}

        base_uri = raw_crash.get('base_uri', "BASE")
        project_id = raw_crash.get('project_id', "PROJECT")

        try:
            crash_to_submit['sentry_version'] = raw_crash['sentry_version']
            crash_to_submit['sentry_client'] = raw_crash['sentry_client']
            crash_to_submit['sentry_key'] = raw_crash['sentry_key']
            crash_to_submit['sentry_data'] = json.dumps(
                raw_crash['sentry_data']
            )
        except KeyError:
            self.config.logger.info(
                "%s doesn't have the proper form for a Bixie crash",
                raw_crash.get(
                    'crash_id',
                    raw_crash.get('uuid', 'this crash')
                )
            )
            return

        url_prefix = join(
            self.config.url,
            base_uri,
            'api',
            project_id,
            'store',
        )
        url = "%s/?%s" % (url_prefix, urllib.urlencode(crash_to_submit))

        self.config.logger.debug(url)

        response = urllib2.urlopen(url)
        submission_response = response.read()
        self.config.logger.debug(
            'submission response: %s',
            submission_response
            )
        if self.config.echo_response:
            print submission_response
