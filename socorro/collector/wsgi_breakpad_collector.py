# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import astral
import datetime
import web
import time

from socorro.lib.ooid import createNewOoid
from socorro.lib.util import DotDict
from socorro.collector.throttler import DISCARD, IGNORE
from socorro.lib.datetimeutil import utc_now

from configman import RequiredConfig, Namespace, class_converter


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
    required_config.add_option(
        'accept_submitted_legacy_processing',
        doc='a boolean telling the collector to use a any legacy_processing'
            'flag submitted with the crash',
        default=False
    )
    required_config.add_option(
        'checksum_method',
        doc='a reference to method that accepts a string and calculates a'
            'hash value',
        default='hashlib.md5',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'reject_crash_on_rahukaalam',
        doc='reject crashes during Rahukaalam',
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
        raw_crash.dump_checksums = DotDict()
        for name, value in form.iteritems():
            if isinstance(value, basestring):
                raw_crash[name] = value
            elif hasattr(value, 'file') and hasattr(value, 'value'):
                dumps[name] = value.value
                raw_crash.dump_checksums[name] = \
                    self.config.collector.checksum_method(
                        value.value
                    ).hexdigest()
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

        if ('legacy_processing' not in raw_crash
            or not self.config.collector.accept_submitted_legacy_processing
        ):
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
        if self.config.collector.reject_crash_on_rahukaalam:
            # only accept crash if not currently Rahukaalam
            # http://en.wikipedia.org/wiki/Rahukaalam
            a = astral.Astral()
            latitude_mountain_view = '37.3894'
            longitude_mountain_view = '122.0819'
            now = datetime.datetime.utcnow()
            try:
                a.rahukaalam_utc(now, latitude_mountain_view, longitude_mountain_view)
            except astral.AstralError:
                # throw crash away, for now is an inauspicious time
                return "Rahukaalam=1\n"

        self.config.crash_storage.save_raw_crash(
          raw_crash,
          dumps,
          crash_id
        )
        self.logger.info('%s accepted', crash_id)
        return "CrashID=%s%s\n" % (self.dump_id_prefix, crash_id)
