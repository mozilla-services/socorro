# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace, RequiredConfig
from configman.converters import class_converter, timedelta_converter

from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
    single_value_sql
)
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.database.transaction_executor import TransactionExecutor
from socorro.lib.datetimeutil import utc_now


#==============================================================================
class LegacyNewCrashSource(RequiredConfig):
    """this class is a refactoring of the iteratior portion of the legacy
    Socorro processor.  It isolates just the part of fetching the ooids of
    jobs to be processed"""
    required_config = Namespace()
    required_config.add_option(
        'database_class',
        doc="the class of the database",
        default=ConnectionContext,
        from_string_converter=class_converter
    )
    required_config.add_option(
        'transaction_executor_class',
        default=TransactionExecutor,
        doc='a class that will manage transactions',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'batchJobLimit',
        default=10000,
        doc='the number of jobs to pull in a time',
    )
    required_config.add_option(
        'pollingInterval',
        default='00:00:00',
        doc='the minimum time between normal job polling attempts',
        from_string_converter=timedelta_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, processor_name, quit_check_callback=None):
        self.config = config
        self.database = self.config.database_class(config)
        self.transaction = self.config.transaction_executor_class(
          config,
          self.database,
          quit_check_callback
        )
        self.processor_name = processor_name
        self.processor_id = None
        self.priority_job_set = set()
        try:
            self.priority_jobs_table_name = self.transaction(
              self._create_priority_jobs
            )
        except Exception:
            if self.processor_id:
                self.config.logger.warning(
                  'creating priority jobs table fails - does it already'
                  'exist?  attempting to continue...',
                  exc_info=True
                )
            else:
                self.config.logger.error(
                  'failure trying to fetch processor id',
                  exc_info=True
                )
                raise

    #--------------------------------------------------------------------------
    def _create_priority_jobs(self, connection):
        self.processor_id = single_value_sql(
          connection,
          "select id from processors where name = %s",
          (self.processor_name,)
        )
        priority_jobs_table_name = "priority_jobs_%d" % self.processor_id
        execute_no_results(
          connection,
          "drop table if exists %s" %
              priority_jobs_table_name
        )
        execute_no_results(
          connection,
          "create table %s (uuid varchar(50) not null primary key)" %
              priority_jobs_table_name
        )
        self.config.logger.info(
          'created priority jobs table: %s',
          priority_jobs_table_name
        )
        return priority_jobs_table_name

    #--------------------------------------------------------------------------
    def close(self):
        self.transaction.do_quit_check = False
        self.transaction(
            execute_no_results,
            "drop table %s" % self.priority_jobs_table_name
        )
        self.config.logger.info(
          'deleted priority jobs table: %s',
          self.priority_jobs_table_name
        )

    #--------------------------------------------------------------------------
    def _priority_jobs_iter(self):
        """
        Yields a list of JobTuples pulled from the 'jobs' table for all the
        jobs found in this process' priority jobs table.  If there are no
        priority jobs, yields None.  This iterator is perpetual - it never
        raises the StopIteration exception
        """
        get_priority_jobs_sql = (
            "select"
            "    j.id,"
            "    pj.uuid,"
            "    1,"  # historical reasons - remove eventually
            "    j.starteddatetime "
            "from"
            "    jobs j right join %s pj on j.uuid = pj.uuid"
            % self.priority_jobs_table_name)
        delete_one_priority_job_sql = "delete from %s where uuid = %%s" %  \
            self.priority_jobs_table_name
        priority_jobs_list = []
        while True:
            if not priority_jobs_list:  # no priority jobs, try to find some
                priority_jobs_list = self.transaction(
                    execute_query_fetchall,
                    get_priority_jobs_sql
                )
            if priority_jobs_list:  # iterate through priority jobs
                while priority_jobs_list:
                    a_job_tuple = priority_jobs_list.pop(0)
                    self.transaction(  # remove job from table
                        execute_no_results,
                        delete_one_priority_job_sql,
                        (a_job_tuple[1],)
                    )
                    if a_job_tuple[0] is not None:
                        if a_job_tuple[3]:
                            continue  # the job already started
                        else:
                            self.priority_job_set.add(a_job_tuple[1])
                            yield (a_job_tuple[0],
                                   a_job_tuple[1],
                                   a_job_tuple[2],)
                    else:
                        self.config.logger.debug(
                            "the priority job %s was never found",
                            a_job_tuple[1]
                        )
            else:
                yield None

    #--------------------------------------------------------------------------
    def _normal_jobs_iter(self):
        """
        Yields a list of job tuples pulled from the 'jobs' table for which the
        owner is this process and the started datetime is null.  This iterator
        is perpetual - it never raises the StopIteration exception
        """
        get_normal_job_sql = (
            "select"
            "    j.id,"
            "    j.uuid,"
            "    priority "
            "from"
            "    jobs j "
            "where"
            "    j.owner = %d"
            "    and j.starteddatetime is null "
            "order by queueddatetime"
            "  limit %d" % (self.processor_id,
                            self.config.batchJobLimit))
        normal_jobs_list = []
        last_query_timestamp = utc_now()
        while True:
            polling_threshold = utc_now() - self.config.pollingInterval
            if not normal_jobs_list and \
               last_query_timestamp < polling_threshold:  # get more
                normal_jobs_list = self.transaction(
                    execute_query_fetchall,
                    get_normal_job_sql
                )
                last_query_timestamp = utc_now()
            if normal_jobs_list:
                while normal_jobs_list:
                    yield normal_jobs_list.pop(0)
            else:
                yield None

    #--------------------------------------------------------------------------
    def _job_iter(self):
        """
           a_job_tuple has this form: (jobId, jobUuid, jobPriority) ...
           of which jobPriority is pure excess, and should someday go away
           Yields the next job according to this pattern:
               START
               Attempt to yield a priority job
               If no priority job, attempt to yield a normal job
               If no priority or normal job, yield None
               loop back to START
        """
        priority_job_iter = self._priority_jobs_iter()
        normal_job_iter = self._normal_jobs_iter()
        ooids_already_seen = set()  # to prevent rapid fire repeats
        while (True):
            # try to get a priority job
            current_job_type = 'priority'
            a_job_tuple = priority_job_iter.next()
            if not a_job_tuple:
                # try to get a normal job
                a_job_tuple = normal_job_iter.next()
                current_job_type = 'normal'
            if a_job_tuple:
                if not a_job_tuple[1] in ooids_already_seen:
                    #
                    ooids_already_seen.add(a_job_tuple[1])
                    self.config.logger.debug(
                        "incomingJobStream yielding %s job %s",
                        current_job_type,
                        a_job_tuple[1]
                    )
                    yield a_job_tuple
                else:
                    self.config.logger.debug(
                        "Skipping already seen job %s",
                        a_job_tuple[1]
                    )
            else:
                # reset rapid fire repeat prevention
                ooids_already_seen = set()
                yield None  # nothing to do

    #--------------------------------------------------------------------------
    def __iter__(self):
        """an adapter that allows this class can serve as an iterator in a
        fetch_transform_save app"""
        for a_legacy_job_tuple in self._job_iter():
            if a_legacy_job_tuple:
                yield (a_legacy_job_tuple[1],), {}
            else:
                yield None

    #--------------------------------------------------------------------------
    def __call__(self):
        return self.__iter__()
