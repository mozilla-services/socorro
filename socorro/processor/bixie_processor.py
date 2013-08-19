# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""this file defines the method of converting a bixie raw crash into a
processed crash"""

from configman import Namespace, RequiredConfig
from configman.converters import class_converter
from configman.dotdict import DotDict

from socorro.lib.datetimeutil import utc_now
from socorro.external.postgresql.dbapi2_util import (
    execute_query_fetchall,
)
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.lib.transform_rules import TransformRuleSystem


#==============================================================================
class BixieProcessor(RequiredConfig):
    """this class is a processor algorthim for Bixie suitable for use in the
    'processor_app' introducted in 2012."""

    required_config = Namespace()
    required_config.add_option(
        'database_class',
        doc="the class of the database",
        default=ConnectionContext,
        from_string_converter=class_converter
    )
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
                "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter
    )
    required_config.namespace('statistics')
    required_config.statistics.add_option(
        'stats_class',
        default='socorro.lib.statistics.StatisticsForStatsd',
        doc='name of a class that will gather statistics',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(BixieProcessor, self).__init__()
        self.config = config
        if quit_check_callback:
            self.quit_check = quit_check_callback
        else:
            self.quit_check = lambda: False
        self.database = self.config.database_class(config)
        self.transaction = \
            self.config.transaction_executor_class(
                config,
                self.database,
                self.quit_check
            )

        self.rule_system = TransformRuleSystem()
        self._load_transform_rules()

        self._statistics = config.statistics.stats_class(
            config.statistics,
            self.config.processor_name
        )
        self._statistics.incr('restarts')

    #--------------------------------------------------------------------------
    def reject_raw_crash(self, crash_id, reason):
        self._log_job_start(crash_id)
        self.config.logger.warning('%s rejected: %s', crash_id, reason)
        self._log_job_end(False, crash_id)

    #--------------------------------------------------------------------------
    def convert_raw_crash_to_processed_crash(self, raw_crash, raw_dumps):
        """ This function is run only by a worker thread.
            Given a job, fetch a thread local database connection and the json
            document.  Use these to create the record in the 'reports' table,
            then start the analysis of the dump file.

            input parameters:
                raw_crash - a nested dict of the form outlined at
                            https://gist.github.com/lonnen/dafb5fdf8611201572f1
                raw_dumps - for future use if we choose to add binary
                            attachments to crashes
        """
        raw_crash = DotDict(raw_crash)
        self._statistics.incr('jobs')
        processor_notes = []
        processed_crash = self._create_minimal_processed_crash()
        try:
            self.quit_check()
            crash_id = raw_crash['crash_id']
            started_timestamp = self._log_job_start(crash_id)

            processed_crash.processor.started_timestamp = started_timestamp
            processed_crash.crash_id = raw_crash['crash_id']

            self.rule_system.apply_all_rules(
                raw_crash,
                raw_dumps,
                processed_crash,
                self
            )

            processed_crash.success = True
        except Exception, x:
            self.config.logger.warning(
                'Error while processing %s: %s',
                raw_crash['crash_id'],
                str(x),
                exc_info=True
            )
            processed_crash.success = False
            processor_notes.append('unrecoverable processor error')
            self._statistics.incr('errors')

        processed_crash.processor.notes = processor_notes
        completed_timestamp = utc_now()
        processed_crash.processor.completed_timestamp = completed_timestamp
        self._log_job_end(
            processed_crash.success,
            crash_id
        )
        return processed_crash

    #--------------------------------------------------------------------------
    def _create_minimal_processed_crash(self):
        processed_crash = DotDict()
        processed_crash.processor = DotDict()
        processed_crash.processor.name = self.config.processor_name
        processed_crash.processor.notes = []
        #processed_crash.classifications = DotDict()
        processed_crash.signature = ''
        return processed_crash

    #--------------------------------------------------------------------------
    def _load_transform_rules(self):
        sql = (
            "select predicate, predicate_args, predicate_kwargs, "
            "       action, action_args, action_kwargs "
            "from transform_rules "
            "where "
            "  category = 'processor.bixie'"
        )
        try:
            rules = self.transaction(execute_query_fetchall, sql)
        except Exception:
            self.config.logger.warning(
                'Unable to load transform rules from the database, falling back'
                ' to defaults',
                exc_info=True
            )
            rules = []
        if not rules:
            # if no rules were loaded, fall back to the hard coded rules
            rules = [
                (True,
                     None, None,
                 'socorro.processor.bixie_processor.signature_action',
                     None, None),
                #(True,
                     #None, None,
                 #'socorro.processor.bixie_processor.signature_action',
                     #None, None),
            ]
        self.rule_system.load_rules(rules)

        self.config.logger.debug(
            'done loading rules: %s',
            str(self.rule_system.rules)
        )

    #--------------------------------------------------------------------------
    def __call__(self, raw_crash, raw_dumps):
        self.convert_raw_crash_to_processed_crash(raw_crash, raw_dumps)

    #--------------------------------------------------------------------------
    def _log_job_start(self, crash_id):
        self.config.logger.info("starting job: %s", crash_id)
        started_datetime = utc_now()
        return started_datetime

    #--------------------------------------------------------------------------
    def _log_job_end(self, success, crash_id):
        self.config.logger.info(
            "finishing %s job: %s",
            'successful' if success else 'failed',
            crash_id
        )


#------------------------------------------------------------------------------
def signature_action(raw_crash, dumps, processed_crash, processor):
    try:
        top_frame = \
            raw_crash['sentry_data']['sentry.interfaces.Stacktrace'] \
                     ['frames'][0]
    except (IndexError, KeyError):
        top_frame = {}
    processed_crash.signature = "%s:%s %s" % (
        top_frame.get('filename', 'unknown file'),
        top_frame.get('lineno', '?'),
        top_frame.get('function', 'unknown fn'),
    )
