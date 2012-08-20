# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import web
import time

from socorro.lib.ooid import createNewOoid
from socorro.lib.util import DotDict
from socorro.collector.throttler import DISCARD
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
    def make_raw_crash(self, form):
        raw_crash = DotDict()
        for name in form.keys():
            if isinstance(form[name], basestring):
                raw_crash[name] = form[name]
            else:
                raw_crash[name] = form[name].value
        raw_crash.timestamp = time.time()
        return raw_crash

    #--------------------------------------------------------------------------
    def POST(self, *args):
        the_form = web.input()
        dump = the_form[self.dump_field]

        import sys

        # Remove other submitted files from the input form, which are
        # an indication of a multi-dump hang submission we aren't yet
        # prepared to handle.
        for (key, value) in web.webapi.rawinput().iteritems():
            if hasattr(value, 'file') and hasattr(value, 'value'):
                print >>sys.stderr, "Removing %s from form" % key
                del the_form[key]

        raw_crash = self.make_raw_crash(the_form)

        current_timestamp = utc_now()
        raw_crash.submitted_timestamp = current_timestamp.isoformat()

        crash_id = createNewOoid(current_timestamp)
        self.logger.info('%s received', crash_id)

        raw_crash.legacy_processing = self.throttler.throttle(raw_crash)
        if raw_crash.legacy_processing == DISCARD:
            return "Discarded=1\n"

        self.config.crash_storage.save_raw_crash(
          raw_crash,
          dump,
          crash_id
        )
        return "CrashID=%s%s\n" % (self.dump_id_prefix, crash_id)
