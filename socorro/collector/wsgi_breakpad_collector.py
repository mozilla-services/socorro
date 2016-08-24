# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time

from socorrolib.lib.ooid import createNewOoid
from socorro.collector.throttler import ACCEPT, DEFER, DISCARD, IGNORE
from socorrolib.lib.datetimeutil import utc_now
from socorro.collector.wsgi_generic_collector import GenericCollectorBase

from configman import Namespace, class_converter


#==============================================================================
class BreakpadCollectorBase(GenericCollectorBase):
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
        'accept_submitted_legacy_processing',
        doc='a boolean telling the collector to use a any legacy_processing'
            'flag submitted with the crash',
        default=False
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(BreakpadCollectorBase, self).__init__(config)
        self.dump_field = self._get_dump_field()
        self.dump_id_prefix = self._get_dump_id_prefix()
        self.accept_submitted_legacy_processing = \
            self._get_accept_submitted_legacy_processing()
        self.throttler = self._get_throttler()
        self.metrics = self._get_metrics()
        self.crash_storage = self._get_crash_storage()

    #--------------------------------------------------------------------------
    def _get_dump_field(self):
        return self.config.dump_field

    #--------------------------------------------------------------------------
    def _get_dump_id_prefix(self):
        return self.config.dump_id_prefix

    #--------------------------------------------------------------------------
    def _get_accept_submitted_legacy_processing(self):
        return self.config.accept_submitted_legacy_processing

    #--------------------------------------------------------------------------
    def _get_metrics(self):
        return self.config.metrics

    #--------------------------------------------------------------------------
    def _get_crash_storage(self):
        return self.config.crash_storage

    #--------------------------------------------------------------------------
    def POST(self, *args):
        raw_crash, dumps = self._get_raw_crash_from_form()

        current_timestamp = utc_now()
        raw_crash.submitted_timestamp = current_timestamp.isoformat()
        # legacy - ought to be removed someday
        raw_crash.timestamp = time.time()

        if (not self.accept_submitted_crash_id or 'uuid' not in raw_crash):
            crash_id = createNewOoid(current_timestamp)
            raw_crash.uuid = crash_id
            self.logger.info('%s received', crash_id)
        else:
            crash_id = raw_crash.uuid
            self.logger.info('%s received with existing crash_id:', crash_id)

        if ('legacy_processing' not in raw_crash
            or not self.accept_submitted_legacy_processing
        ):
            raw_crash.legacy_processing, raw_crash.throttle_rate = (
                self.throttler.throttle(raw_crash)
            )
        else:
            raw_crash.legacy_processing = int(raw_crash.legacy_processing)


        try:
            # We want to capture the crash report size, but need to
            # differentiate between compressed vs. uncompressed data as well as
            # accepted vs. rejected data.
            crash_report_size = self._get_content_length()
            is_compressed = self._is_content_gzipped()
            is_accepted = (raw_crash.legacy_processing in (ACCEPT, DEFER))

            metrics_data = {}
            size_key = '_'.join([
                'crash_report_size',
                'accepted' if is_accepted else 'rejected',
                'compressed' if is_compressed else 'uncompressed',
            ])
            metrics_data = {
                size_key: crash_report_size
            }
            self.metrics.capture_stats(metrics_data)
        except Exception:
            # We *never* want metrics reporting to prevent saving a crash, so
            # we catch everything and log an error.
            self.logger.error(
                'metrics kicked up exception',
                exc_info=True
            )

        if raw_crash.legacy_processing == DISCARD:
            self.logger.info('%s discarded', crash_id)
            return "Discarded=1\n"
        if raw_crash.legacy_processing == IGNORE:
            self.logger.info('%s ignored', crash_id)
            return "Unsupported=1\n"

        raw_crash.type_tag = self.dump_id_prefix.strip('-')

        # Save crash to storage.
        self.crash_storage.save_raw_crash(
            raw_crash,
            dumps,
            crash_id
        )

        # Return crash id to http client.
        self.logger.info('%s accepted', crash_id)
        return "CrashID=%s%s\n" % (self.dump_id_prefix, crash_id)


#==============================================================================
class BreakpadCollector(BreakpadCollectorBase):
    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

    #--------------------------------------------------------------------------
    uri = '/submit'
    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------
    def _get_throttler(self):
        return self.config.throttler

    #--------------------------------------------------------------------------
    def _get_dump_field(self):
        return self.config.collector.dump_field

    #--------------------------------------------------------------------------
    def _get_dump_id_prefix(self):
        return self.config.collector.dump_id_prefix

    #--------------------------------------------------------------------------
    def _get_accept_submitted_legacy_processing(self):
        return self.config.collector.accept_submitted_legacy_processing

    #--------------------------------------------------------------------------
    def _get_checksum_method(self):
        return self.config.collector.checksum_method

    #--------------------------------------------------------------------------
    def _get_accept_submitted_crash_id(self):
        return self.config.collector.accept_submitted_crash_id


#==============================================================================
class BreakpadCollector2015(BreakpadCollectorBase):
    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()
    #--------------------------------------------------------------------------
    # throttler namespace
    #     the namespace is for config parameters for the throttler system
    #--------------------------------------------------------------------------
    required_config.namespace('throttler')
    required_config.throttler.add_option(
        'throttler_class',
        default='socorro.collector.throttler.LegacyThrottler',
        doc='the class that implements the throttling action',
        from_string_converter=class_converter
    )
    #--------------------------------------------------------------------------
    # metrics namespace
    #     the namespace is for config parameters for the metrics system
    #--------------------------------------------------------------------------
    required_config.namespace('metrics')
    required_config.metrics.add_option(
        'metrics_class',
        default='socorro.external.metrics_base.MetricsBase',
        doc='the class that implements metrics; no value means no metrics',
        from_string_converter=class_converter
    )
    #--------------------------------------------------------------------------
    # storage namespace
    #     the namespace is for config parameters crash storage
    #--------------------------------------------------------------------------
    required_config.namespace('storage')
    required_config.storage.add_option(
        'crashstorage_class',
        doc='the source storage class',
        default='socorro.external.fs.crashstorage'
                '.FSLegacyDatedRadixTreeStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def _get_throttler(self):
        try:
            return self.config.throttler.throttler_instance
        except KeyError:
            self.config.throttler.throttler_instance = \
                self.config.throttler.throttler_class(self.config.throttler)
            return self.config.throttler.throttler_instance

    #--------------------------------------------------------------------------
    def _get_metrics(self):
        try:
            return self.config.metrics.metrics_instance
        except KeyError:
            self.config.metrics.metrics_instance = \
                self.config.metrics.metrics_class(self.config.metrics)
            return self.config.metrics.metrics_instance

    #--------------------------------------------------------------------------
    def _get_crash_storage(self):
        try:
            return self.config.storage.storage_instance
        except KeyError:
            self.config.storage.storage_instance = \
                self.config.storage.crashstorage_class(
                    self.config.storage
                )

            return self.config.storage.storage_instance
