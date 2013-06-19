# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import web
import time
import json

from socorro.lib.ooid import createNewOoid
from socorro.lib.util import DotDict
from socorro.collector.throttler import DISCARD, IGNORE
from socorro.lib.datetimeutil import utc_now

from configman import RequiredConfig, Namespace


#==============================================================================
class BixieCollector(RequiredConfig):
    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.logger = self.config.logger
        self.throttler = config.throttler
        self.crash_storage = config.crash_storage

    #--------------------------------------------------------------------------
    # cannonical BASE_URI/api/PROJECT_ID/store/`,
    uri = '/(.*)/api/(.*)/store/'
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def GET(self, *args):
        current_timestamp = utc_now()
        base_uri, project_id = args

        raw_crash = DotDict(web.input())
        raw_crash.base_uri = base_uri
        raw_crash.project_id = project_id
        raw_crash.sentry_data = json.loads(raw_crash.sentry_data)
        raw_crash.submitted_timestamp = current_timestamp.isoformat()
        raw_crash.crash_id = createNewOoid(current_timestamp)
        #raw_crash.throttle = self.throttler.throttle(raw_crash)

        self.config.crash_storage.save_raw_crash(
          raw_crash,
          {},
          raw_crash.crash_id
        )
        self.logger.info('%s accepted', raw_crash.crash_id)

        return 'ok'
