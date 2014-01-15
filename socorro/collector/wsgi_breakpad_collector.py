# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import web
import time

from socorro.lib.ooid import createNewOoid
from socorro.lib.util import DotDict
from socorro.collector.throttler import DISCARD, IGNORE
from socorro.lib.datetimeutil import utc_now

from configman import RequiredConfig, Namespace


#==============================================================================
class BreakpadCollector(RequiredConfig):
    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()
    required_config.add_option(
        'dump_field',
        doc='the name of the form field containing the raw dump',
        default='upload_file_minidump'
    )
    required_config.add_option(
        'dump_id_prefix',
        doc='the prefix to return to the client in front of the OOID',
        default='bp-'
    )
    required_config.add_option(
        'accept_submitted_crash_id',
        doc='a boolean telling the collector to use a crash_id provided in '
            'the crash submission',
        default=False
    )

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
            elif isinstance(value, int):
                raw_crash[name] = value
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

        if (not self.config.collector.accept_submitted_crash_id
            or 'uuid' not in raw_crash
        ):
            crash_id = createNewOoid(current_timestamp)
            raw_crash.uuid = crash_id
            self.logger.info('%s received', crash_id)
        else:
            crash_id = raw_crash.uuid
            self.logger.info('%s received with existing crash_id:', crash_id)

        if 'legacy_processing' not in raw_crash:
            raw_crash.legacy_processing, raw_crash.throttle_rate = (
                self.throttler.throttle(raw_crash)
            )
        else:
            raw_crash.legacy_processing = int(raw_crash.legacy_processing)
        if raw_crash.legacy_processing == DISCARD:
            self.logger.info('%s discarded', crash_id)
            return "Discarded=1\n"
        if raw_crash.legacy_processing == IGNORE:
            self.logger.info('%s ignored', crash_id)
            return "Unsupported=1\n"

        self.config.crash_storage.save_raw_crash(
          raw_crash,
          dumps,
          crash_id
        )
        self.logger.info('%s accepted', crash_id)
        return "CrashID=%s%s\n" % (self.dump_id_prefix, crash_id)
