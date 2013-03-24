# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import web
import time

from socorro.lib.ooid import createNewOoid
from socorro.lib.util import DotDict
from socorro.collector.throttler import DISCARD, IGNORE
from socorro.lib.datetimeutil import utc_now


#==============================================================================
class Collector(object):
    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.logger = self.config.logger
        self.throttler = config.throttler
        self.dump_id_prefix = config.collector.dump_id_prefix
        self.crash_storage = config.crash_storage
        self.dump_field = config.collector.dump_field

    #--------------------------------------------------------------------------
    uri = '/submit'
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def _make_raw_crash_and_dumps(self, form):
        dumps = DotDict()
        raw_crash = DotDict()
        for name, value in form.iteritems():
            if isinstance(value, basestring):
                raw_crash[name] = value
            elif hasattr(value, 'file') and hasattr(value, 'value'):
                dumps[name] = value.value
            else:
                raw_crash[name] = value.value
        return raw_crash, dumps

    #--------------------------------------------------------------------------
    def POST(self, *args):
        # default values for benchmarking.  The benchmark logging is machine
        # readable in json format, so these failure strings need json string
        # quoting, hense the double quotes inside the single quotes.
        result = '"failed"'
        reading_time = '"failed"'
        throttle_time = '"incomplete"'
        save_raw_crash_time = '"incomplete"'

        current_timestamp = utc_now()
        crash_id = createNewOoid(current_timestamp)
        try:
            reading_form_timestamp = time.time()
            raw_crash, dumps = \
                self._make_raw_crash_and_dumps(web.webapi.rawinput())
            reading_time = "%2.2f" % (time.time() - reading_form_timestamp)

            raw_crash.submitted_timestamp = current_timestamp.isoformat()
            # legacy - ought to be removed someday
            raw_crash.timestamp = time.time()

            throttle_timestamp = raw_crash.timestamp
            raw_crash.legacy_processing = self.throttler.throttle(raw_crash)
            throttle_time = "%2.4f" % (time.time() - throttle_timestamp)
            if raw_crash.legacy_processing == DISCARD:
                result = 'discarded'
                return "Discarded=1\n"
            if raw_crash.legacy_processing == IGNORE:
                result = 'unsupported'
                return "Unsupported=1\n"

            save_raw_crash_timestamp = time.time()
            self.config.crash_storage.save_raw_crash(
              raw_crash,
              dumps,
              crash_id
            )
            save_raw_crash_time = \
                "%2.2f" % (time.time() - save_raw_crash_timestamp)
            result = 'saved'
            return "CrashID=%s%s\n" % (self.dump_id_prefix, crash_id)
        finally:
            self.logger.info(
                '%s - benchmark {"action": "%s", '
                '"reading_form": %s, '
                '"throttling": %s, '
                '"save_raw_crash": %s}',
                crash_id,
                result,
                reading_time,
                throttle_time,
                save_raw_crash_time
            )
