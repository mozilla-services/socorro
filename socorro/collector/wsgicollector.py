# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# this is the collector service for the OLD STYLE collector
# TODO: replace with new style collector

import web
import time
import logging

logger = logging.getLogger("collector")

from socorro.lib.ooid import createNewOoid
from socorro.lib.datetimeutil import utc_now
from socorro.storage.crashstorage import LegacyThrottler

from socorro.external.crashstorage_base import PolyStorageError

from socorro.lib.util import DotDict


#==============================================================================
class Collector(object):
    #--------------------------------------------------------------------------
    def __init__(self, context):
        self.context = context
        self.logger = self.context.setdefault('logger', logger)
        self.legacy_throttler = context.legacyThrottler
        self.dump_id_prefix = context.dumpIDPrefix
        self.dump_field = context.dumpField

    #--------------------------------------------------------------------------
    uri = '/submit'

    #--------------------------------------------------------------------------
    def _make_raw_crash_and_dumps(self, form):
        dumps = DotDict()
        raw_crash = DotDict()
        for name, value in form.iteritems():
            if isinstance(value, basestring):
                raw_crash[name] = v
            elif hasattr(value, 'file') and hasattr(value, 'value'):
                dumps[name] = value.value
            else:
                raw_crash[name] = value.value
        return raw_crash, dumps

    #--------------------------------------------------------------------------
    def POST(self, *args):
        raw_crash, dumps = \
            self._make_raw_crash_and_dumps(web.webapi.rawinput())

        current_timestamp = utc_now()
        raw_crash.submitted_timestamp = current_timestamp.isoformat()
        # legacy - ought to be removed someday
        raw_crash.timestamp = time.time()

        crash_id = createNewOoid(current_timestamp)

        raw_crash.legacy_processing = self.legacy_throttler.throttle(raw_crash)
        if raw_crash.legacy_processing == LegacyThrottler.DISCARD:
            self.logger.info('%s discarded', crash_id)
            return "Discarded=1\n"
        if raw_crash.legacy_processing == LegacyThrottler.IGNORE:
            self.logger.info('%s ignored', crash_id)
            return "Unsupported=1\n"

        crash_storage = self.context.crashStoragePool.crashStorage()
        try:
            crash_storage.save_raw_crash(
                raw_crash,
                dumps,
                crash_id
            )
        except PolyStorageError, x:
            self.logger.error('%s storage exception: %s',
                              crash_id,
                              str(x.exceptions),  # log internal error set
                              exc_info=True)
            raise
        self.logger.info('%s accepted', crash_id)
        return "CrashID=%s%s\n" % (self.dump_id_prefix, crash_id)
