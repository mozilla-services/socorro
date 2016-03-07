# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# these processor rule and new crash source classes were written as a
# solution to Bug 1087414.  They are NOT for general use within a processor.

from datetime import timedelta, datetime

from socorrolib.lib.transform_rules import Rule
from socorro.external.postgresql.dbapi2_util import execute_query_fetchall
from socorrolib.lib.datetimeutil import string_to_datetime, date_to_string

from configman import Namespace, RequiredConfig, class_converter
from configman.converters import str_to_timedelta, to_str

#==============================================================================
class DateProcessedTimeMachine(Rule):
    required_config = Namespace()
    required_config.add_option(
        name='crashstorage_class',
        doc='the crash storage system class',
        default='socorro.external.boto.crashstorage.BotoS3CrashStorage',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'time_delta',
        doc='how much to change the date_processed into the past',
        default='0 08:00:00',  # 8 hours
        from_string_converter=str_to_timedelta
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(DateProcessedTimeMachine, self).__init__(config)
        self.crashstore = config.crashstorage_class(config)

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        crash_id = raw_crash.uuid
        old_processed_crash = self.crashstore.get_unredacted_processed(crash_id)

        for key, value in old_processed_crash.iteritems():
            if 'date_processed' in key:
                processed_crash[key] = date_to_string(
                    string_to_datetime(value) - self.config.time_delta
                )
                print processed_crash.uuid, value, processed_crash[key]
            else:
                if key != 'uptime' and key != 'crash_time' and (
                   'time' in key or "date" in key or 'Date' in key
                ):
                    value = date_to_string(string_to_datetime(value))
                processed_crash[key] = value
        processor_meta.processor_notes.append(
            'DateProcessedTimeMachine has pushed date_processed into the past'
            ' by "%s" (D HH:MM:SS)' %  to_str(self.config.time_delta)
        )
        processor_meta.processor_notes.append(
            'Original processor_notes: %s'
            % old_processed_crash['processor_notes']
        )
        return True

#==============================================================================
# this class was relocated to a more appropriate module.  This import is
# offered for backwards compatibility
from socorro.external.postgresql.new_crash_source import PGQueryNewCrashSource
