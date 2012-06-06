"""the monitor_app manages the jobs queue and their processor assignments"""

import signal
import threading
import time

from configman import Namespace
from configman.converters import class_converter, timedelta_converter

from socorro.app.generic_app import App, main
from socorro.lib.datetimeutil import utc_now

from socorro.external.postgresql.dbapi2_util import (
  single_value_sql,
  single_row_sql,
  execute_query_fetchall,
  execute_no_results,
  SQLDidNotReturnSingleValue
)


#------------------------------------------------------------------------------
def timedelta_to_seconds_coverter(td_str):
    td = timedelta_converter(td_str)
    return td.seconds + td.days * 24 * 3600


#==============================================================================
class NoProcessorsRegisteredError (Exception):
    pass


#==============================================================================
class MonitorApp(App):
    """the MonitorApp class is responsible for gathering new crashes and
    assigning them to processors.  It implements a queue within the 'jobs'
    table in Posgres.  This class is multithread hot, creating three thread in
    addition to the MainThread:

        standard_job_thread - this thread polls the 'new_crash_source' for new
                              crashes.  New crashes are entered into the It
                              allocates new crashes to registered
                              processors in a balanced manner making sure that
                              no processor is overloaded.
        priority_job_thread - this thread polls the 'priorityjobs' table in
                              postgres for crashes requesting immediate
                              processing.  It assigns jobs in an unbalanced
                              manner assuming that the processors to which it
                              assigns jobs will do them immediately without
                              regard to their queue size.
        job_cleanup_thread - this thread simply maintains the internal 'jobs'
                             table.  It deletes completed queue entries.  It
                             looks for stalled jobs and resets.
    """
    app_name = 'monitor_app'
    app_version = '3.0'
    app_description = __doc__

    required_config = Namespace()
    # configuration is broken into three namespaces: registrar, new_crash_source,
    # and job_manager

    #--------------------------------------------------------------------------
    # registrar namespace
    #     this namespace is for config parameters having to do with registering
    #     and maintaining the list of processors available
    #--------------------------------------------------------------------------
    required_config.namespace('registrar')
    required_config.registrar.add_option(
      'database_class',
      doc="the class of the registrar's database",
      default='socorro.external.postgresql.connection_context.'
              'ConnectionContext',
      from_string_converter=class_converter
    )
    required_config.registrar.add_option(
      'transaction_executor_class',
      default='socorro.database.transaction_executor.TransactionExecutor',
      doc="a class that will manage the registrar's transactions",
      from_string_converter=class_converter
    )
    required_config.registrar.add_option(
      'sweep_frequency',
      default='00:02:00',
      doc='frequency for cleaning up dead processors',
      from_string_converter=timedelta_to_seconds_coverter
    )
    required_config.registrar.add_option(
      'processor_grace_period',
      default='00:02:00',
      doc="a processor is dead if it is this late to renew registration",
      from_string_converter=timedelta_converter
    )
    required_config.registrar.add_option(
      'check_in_frequency',
      doc='how often the processor is required to reregister (hh:mm:ss)',
      default="00:01:00",
      from_string_converter=timedelta_converter
    )
    required_config.registrar.add_option(
      'quit_if_no_processors',
      doc='die if there are no live processors running',
      default=False,
    )

    #--------------------------------------------------------------------------
    # new_crash_source namespace
    #     this namespace is for config parameter having to do with the source
    #     of new ooids.  This generally for a crashstorage class that
    #     implements the 'new_ooids' iterator
    #--------------------------------------------------------------------------
    required_config.namespace('new_crash_source')
    required_config.new_crash_source.add_option(
      'new_crash_source_class',
      doc='an iterable that will stream ooids needing processing',
      default='socorro.monitor.crashstore_new_crash_source.CrashStorageNewCrashSource',
      from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    # job_manager namespace
    #     this namespace is for config parameter having to do with maintaining
    #     the 'jobs' and  'priortityjobs' tables and assigning jobs to
    #     processors.
    #--------------------------------------------------------------------------
    required_config.namespace('job_manager')
    required_config.job_manager.add_option(
      'database_class',
      doc="the class of the job_manager's database",
      default='socorro.external.postgresql.connection_context.'
              'ConnectionContext',
      from_string_converter=class_converter
    )
    required_config.job_manager.add_option(
      'transaction_executor_class',
      default='socorro.database.transaction_executor.TransactionExecutor',
      doc="a class that will manage the job_manager's transactions",
      from_string_converter=class_converter
    )
    required_config.job_manager.add_option(
      'standard_loop_frequency',
      default='00:02:00',
      doc="the frequency to check for new jobs (hh:mm:ss)",
      from_string_converter=timedelta_to_seconds_coverter
    )
    required_config.job_manager.add_option(
      'priority_loop_frequency',
      default='00:00:30',
      doc="the frequency to check for new priority jobs (hh:mm:ss)",
      from_string_converter=timedelta_to_seconds_coverter
    )
    required_config.job_manager.add_option(
      'job_cleanup_frequency',
      default='00:05:00',
      doc="the frequency to check for new jobs (hh:mm:ss)",
      from_string_converter=timedelta_to_seconds_coverter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(MonitorApp, self).__init__(config)
        self.registrar_database = config.registrar.database_class(
          config.registrar
        )
        self.registrar_transaction = \
          config.registrar.transaction_executor_class(
            config.registrar,
            self.registrar_database,
            quit_check_callback=self._quit_check
          )

        self.job_manager_database = config.job_manager.database_class(
          config.job_manager
        )
        self.job_manager_transaction = \
          config.job_manager.transaction_executor_class(
            config.job_manager,
            self.registrar_database,
            quit_check_callback=self._quit_check
          )

        self.new_crash_source = config.new_crash_source.new_crash_source_class(
          config.new_crash_source,
          ''
        )

        signal.signal(signal.SIGTERM, self._respond_to_SIGTERM)
        signal.signal(signal.SIGHUP, self._respond_to_SIGTERM)

        self.quit = False

    #--------------------------------------------------------------------------
    #  utilities section
    #--------------------------------------------------------------------------
    def _respond_to_SIGTERM(self, signal_number, frame):
        """these classes are instrumented to respond to a KeyboardInterrupt by
        cleanly shutting down. This function, when given as a handler to for a
        SIGTERM event, will make the program respond to a SIGTERM as neatly as
        it responds to ^C."""
        signame = 'SIGTERM'
        if signal_number != signal.SIGTERM:
            signame = 'SIGHUP'
        self.config.logger.info("%s detected", signame)
        raise KeyboardInterrupt

    #--------------------------------------------------------------------------
    def _quit_check(self):
        """this a callback function to be propagated through out the system.
        threads should periodically call this function so see if they should
        shutdown"""
        if self.quit:
            self.config.logger.debug('quit signal acknowledged')
            raise KeyboardInterrupt

    #--------------------------------------------------------------------------
    def _responsive_sleep(self, seconds):
        """the threads spend most of their time sleeping.  Even though they're
        not doing work, they need to contuously poll the quit function so
        that the monitor can shut down promptly on request.  This function
        sleeps, polling the quit function each second."""
        self.config.logger.info('sleeping for %s seconds', seconds)
        for x in xrange(int(seconds)):
            self._quit_check()
            time.sleep(1.0)

    #--------------------------------------------------------------------------
    def _responsive_join(self, thread):
        """similar to the responsive sleep, a join function blocks a thread
        until some other thread dies.  If it doesn't happen to be the main
        thread waitng, it'll need to poll the quit function peroidically to
        know if it should quit.

        parameters:
            thread - an instance of the TaskThread class representing the
                     thread to wait for
        """
        while True:
            try:
                thread.join(1.0)
                if not thread.isAlive():
                    break  # no use waiting for a thread that isn't there
                self._quit_check()
            except KeyboardInterrupt:
                self.config.logger.debug('quit detected by _responsive_join')
                self.quit = True

    #--------------------------------------------------------------------------
    #  job manager section
    #--------------------------------------------------------------------------
    def _clean_jobs_table_transaction(self, connection):
        """go through the jobs table and remove jobs that are complete"""
        self.config.logger.debug("removing completed jobs from queue")
        self.config.logger.debug("starting deletion")
        execute_no_results(
          connection,
          "delete from jobs "
          "where"
          "    uuid in (select "
          "                 uuid"
          "             from"
          "                 jobs j"
          "             where"
          "                 j.success is not null)"
        )

    #--------------------------------------------------------------------------
    def _kick_stalled_jobs_transaction(self, connection):
        """try to restart stalled jobs by changing the startteddatetime to
        NULL.  This should get the attention of the assigned processor"""
        self.config.logger.debug("restart stalled jobs in queue")
        execute_no_results(
          connection,
          "update jobs "
          "    set starteddatetime = NULL "
          "where"
          "    success is NULL"
          "    and completeddatetime is NULL"
          "    and starteddatetime < now() - %s - %s",
          (self.config.registrar.check_in_frequency,
           self.config.registrar.processor_grace_period)
        )

    #--------------------------------------------------------------------------
    def _job_cleanup_thread(self):
        """this is the main rountine for the job_cleanup_thread.  Each cycle
        does three transactions: the first deletes completed jobs; the second
        kicks stalled jobs; the third removes dead processors"""
        self.config.logger.info("job_cleanup_loop starting.")
        try:
            while True:
                try:
                    self.config.logger.info("begin _job_cleanup_thread cycle")
                    self.job_manager_transaction(
                      self._clean_jobs_table_transaction
                    )
                    self.job_manager_transaction(
                      self._kick_stalled_jobs_transaction
                    )
                    self.registrar_transaction(
                      self._sweep_dead_processors_transaction
                    )
                    self.config.logger.info(
                      "beginning _job_cleanup_thread cycle."
                    )
                    self.config.logger.info("end _job_cleanup_thread cycle")
                    self._responsive_sleep(
                      self.config.job_manager.job_cleanup_frequency
                    )
                except (KeyboardInterrupt, SystemExit):
                    #self.config.logger.debug("got quit message")
                    self.quit = True
                    break
                except Exception:
                    self.config.logger.warning(
                      'unexpected exception',
                      exc_info=True)
        finally:
            self.config.logger.info("job_cleanup_loop done.")

    #--------------------------------------------------------------------------
    #  processor management section
    #--------------------------------------------------------------------------
    def _sweep_dead_processors_transaction(self, connection):
        """this function is a single database transaction: look for dead
        processors - find all the jobs of dead processors and assign them to
        live processors then delete the dead processor registrations"""
        self.config.logger.info("looking for dead processors")
        try:
            self.config.logger.info(
              "threshold %s",
              self.config.registrar.check_in_frequency
            )
            threshold = single_value_sql(
              connection,
              "select now() - %s - %s",
              (self.config.registrar.processor_grace_period,
               self.config.registrar.check_in_frequency)
            )
            dead_processors = execute_query_fetchall(
              connection,
              "select id from processors where lastSeenDateTime < %s",
              (threshold,)
            )
            if dead_processors:
                self.config.logger.info("found dead processor(s):")
                for a_dead_processor in dead_processors:
                    self.config.logger.info("%d is dead", a_dead_processor[0])

                self.config.logger.debug("getting list of live processor(s):")
                live_processors = execute_query_fetchall(
                  connection,
                  "select id from processors where lastSeenDateTime >= %s",
                  (threshold,)
                )
                if not live_processors:
                    if self.config.registrar.quit_if_no_processors:
                        raise NoProcessorsRegisteredError(
                          "There are no processors registered"
                        )
                    else:
                        self.config.logger.critical(
                          'There are no live processors, nothing to do. '
                          'Waiting for processors to come on line.'
                        )
                        return
                number_of_live_processors = len(live_processors)

                self.config.logger.debug(
                  "getting range of queued date for jobs associated with "
                  "dead processor(s):"
                )
                dead_processor_ids_str = ", ".join(
                  [str(x[0]) for x in dead_processors]
                )
                earliest_dead_job, latest_dead_job = single_row_sql(
                  connection,
                  "select min(queueddatetime), max(queueddatetime) from jobs "
                      "where owner in (%s)" % dead_processor_ids_str
                )
                # take dead processor jobs and reallocate them to live
                # processors in equal sized chunks
                if (earliest_dead_job is not None and
                  latest_dead_job is not None):
                    time_increment = (
                      (latest_dead_job - earliest_dead_job) /
                      number_of_live_processors
                    )
                    for x, live_processor_id in enumerate(live_processors):
                        low_queued_time = (
                          x * time_increment + earliest_dead_job
                        )
                        high_queued_time = (
                          (x + 1) * time_increment + earliest_dead_job
                        )
                        self.config.logger.info(
                          "assigning jobs from %s to %s to processor %s:",
                          low_queued_time,
                          high_queued_time,
                          live_processor_id
                        )
                        # why is the range >= at both ends? the range must be
                        # inclusive, the risk of moving a job twice is low and
                        # consequences low, too.
                        # 1st step: take any jobs of a dead processor that were
                        # in progress and reset them to unprocessed
                        execute_no_results(
                          connection,
                          "update jobs set"
                          "    starteddatetime = NULL "
                          "where"
                          "    %%s >= queueddatetime"
                          "    and queueddatetime >= %%s"
                          "    and owner in (%s)"
                          "    and success is NULL" % dead_processor_ids_str,
                          (high_queued_time, low_queued_time)
                        )
                        # 2nd step: take all jobs of a dead processor and give
                        # them to a new owner
                        execute_no_results(
                          connection,
                          "update jobs set"
                          "    set owner = %%s "
                          "where"
                          "    %%s >= queueddatetime"
                          "    and queueddatetime >= %%s"
                          "    and owner in (%s)" % dead_processor_ids_str,
                          (live_processor_id, high_queued_time,
                           low_queued_time)
                        )

                # transfer stalled priority jobs to new processors
                for dead_processor_tuple in dead_processors:
                    self.config.logger.info(
                      "re-assigning priority jobs from processor %d:",
                      dead_processor_tuple[0]
                    )
                    execute_no_results(
                      connection,
                      "insert into priorityjobs (uuid) select uuid "
                      "from priority_jobs_%d" % dead_processor_tuple
                    )

                self.config.logger.info("removing all dead processors")
                execute_no_results(
                  connection,
                  "delete from processors where lastSeenDateTime < %s",
                  (threshold,)
                )
                # remove dead processors' priority tables
                for a_dead_processor in dead_processors:
                    execute_no_results(
                      connection,
                      "drop table if exists priority_jobs_%d" %
                        a_dead_processor[0]
                    )
        except NoProcessorsRegisteredError:
            self.quit = True
            self.config.logger.critical('there are no live processors')

    #--------------------------------------------------------------------------
    def _get_processors_and_loads_transaction(self, connection):
        """this transaction fetches a list of live processors and how many
        jobs each curretly has assigned to it"""
        sql = ("with live_processors as "
               "    (select * from processors where "
               "     lastSeenDateTime > now() - %s)"
               "select"
               "    p.id,"
               "    count(j.owner) "
               "from"
               "    live_processors p left join jobs j "
               "        on p.id = j.owner"
               "           and j.success is null "
               "group by p.id")
        processors_and_load = execute_query_fetchall(
          connection,
          sql,
          (self.config.registrar.check_in_frequency,)
        )
        # convert row tuples to muteable lists
        return [[a_row[0], a_row[1]] for a_row in processors_and_load]

    #--------------------------------------------------------------------------
    def _balanced_processor_iter(self):
        """ This takes a snap shot of the state of the processors as well as
        the number of jobs assigned to each then acts as an iterator that
        returns a sequence of processor ids.  Order of ids returned will assure
        that jobs are assigned in a balanced manner.

        This iterator is infinite.  It never raises StopIteration.  How does
        it ever quit?  It is run in parallel with the iterator that fetches
        a batch of ooids from the ooid source by the '_standard_job_thread'
        method.  When that iterator is exhausted, this iterator is thrown away.
        On the next batch of ooids, a new copy of this iterator is created."""
        self.config.logger.debug(
          "balanced _balanced_processor_iter: compiling list of active "
          "processors"
        )
        try:
            list_of_processors_and_loads = self.job_manager_transaction(
              self._get_processors_and_loads_transaction
            )
            self.config.logger.debug(
              "list_of_processors_and_loads: %s",
              str(list_of_processors_and_loads)
            )
            if not list_of_processors_and_loads:
                if self.config.registrar.quit_if_no_processors:
                    raise NoProcessorsRegisteredError(
                      "There are no processors registered"
                    )
                else:
                    self.config.logger.critical(
                      "There are no live processors. "
                      "Waiting for processors to come on line"
                    )
                    yield None
            while True:
                self.config.logger.debug(
                  "sort the list of (processorId, numberOfAssignedJobs) pairs"
                )
                list_of_processors_and_loads.sort(lambda x,y: cmp(x[1], y[1]))
                # the processor with the fewest jobs is about to be assigned a
                # new job, so increment its count
                list_of_processors_and_loads[0][1] += 1
                self.config.logger.debug(
                  "yield the processorId which had the fewest jobs: %d",
                  list_of_processors_and_loads[0][0]
                )
                yield list_of_processors_and_loads[0][0]
        except NoProcessorsRegisteredError:
            self.quit = True
            self.config.logger.critical('there are no live processors')
            raise

    #--------------------------------------------------------------------------
    def _get_live_processors_transaction(self, connection):
        """this transaction just fetches a list of live processors"""
        processor_ids = execute_query_fetchall(
          connection,
          "select id from processors "
          "where lastSeenDateTime > now() - interval %s",
          (self.config.registrar.check_in_frequency,)
        )
        # remove the row tuples, just give out a pure list of ids
        return [a_row[0] for a_row in processor_ids]

    #--------------------------------------------------------------------------
    def _unbalanced_processor_iter(self):
        """ This generator returns a sequence of active processorId without
        regard to job balance.  Like its brother, '_balanced_processor_iter',
        it is an infinite iter, never raising 'StopIteration'."""
        self.config.logger.debug(
          "unbalancedJobSchedulerIter: compiling list of active processors"
        )
        try:
            while True:
                list_of_processor_ids = self.job_manager_transaction(
                  self._get_live_processors_transaction
                )
                if not list_of_processor_ids:
                    if self.config.registrar.quit_if_no_processors:
                        raise NoProcessorsRegisteredError(
                          "There are no processors registered"
                        )
                    else:
                        self.config.logger.critical(
                          "There are no live processors. "
                          "Waiting for processors to come on line"
                        )
                        yield None
                for a_processor_id in list_of_processor_ids:
                    self.config.logger.debug(
                      'about to yield %s', a_processor_id
                    )
                    yield a_processor_id
        except NoProcessorsRegisteredError:
            self.quit = True
            self.config.logger.critical('there are no live processors')
            raise

    #--------------------------------------------------------------------------
    #  job queuing section
    #--------------------------------------------------------------------------
    def _queue_standard_job_transaction(self, connection, uuid,
                                        candidate_processor_iter):
        """this method implements a single transaction, inserting a crash into
        the 'jobs' table.  Because the jobs table contains a non-NULL foreign
        key reference to the 'processors' table, the act of insertion is also
        the act of assigning the crash to a processor."""
        #self.config.logger.debug("trying to insert %s", uuid)
        assigned_processor = candidate_processor_iter.next()  # get a processor
        if assigned_processor is None:
            return None
        execute_no_results(
          connection,
          "insert into jobs (pathname, uuid, owner, priority,"
          "                  queuedDateTime) "
          "values (%s, %s, %s, %s, %s)",
          ('', uuid, assigned_processor, 1, utc_now())
        )
        self.config.logger.debug(
          "%s assigned to processor %d", uuid, assigned_processor
        )
        return assigned_processor

    #--------------------------------------------------------------------------
    def _queue_priorty_job_transaction(self, connection, uuid,
                                       candidate_processor_iter):
        """this method implements a transaction, inserting a crash to both
        the 'jobs' table (via the '_queue_standard_job_transaction' method)
        and the 'priority_jobs_XXX' table associated with the target
        processor"""
        #self.config.logger.info('_queue_priorty_job_transaction')
        assigned_processor = self._queue_standard_job_transaction(
          connection,
          uuid,
          candidate_processor_iter
        )
        if assigned_processor is None:
            return None
        execute_no_results(
          connection,
          "insert into priority_jobs_%d (uuid) values (%%s)"
            % assigned_processor,
          (uuid,)
        )
        execute_no_results(
          connection,
          "delete from priorityjobs where uuid = %s",
          (uuid,)
        )
        return assigned_processor

    #--------------------------------------------------------------------------
    def _standard_job_thread(self):
        """This is the main method for the 'standard_job_thread'.  It is
        responsible for iterating through the 'new_crash_source' for new
        crashes, and assigning them to processors.
        """
        try:
            self.config.logger.info("starting _standard_job_thread")
            while (True):
                self.config.logger.info("begin _standard_job_thread cycle")
                self._quit_check()
                # walk the dump indexes and assign jobs
                self.config.logger.debug("getting _balanced_processor_iter")
                processor_iter = self._balanced_processor_iter()
                self.config.logger.debug("scanning for new crashes")
                for uuid in self.new_crash_source():
                    try:
                        self.config.logger.debug("new job: %s", uuid)
                        while True:
                            # retry until we succeed in assigning
                            self._quit_check()
                            assigned_processor = \
                              self.job_manager_transaction(
                                  self._queue_standard_job_transaction,
                                  uuid,
                                  processor_iter
                                )
                            if assigned_processor is not None:
                                break
                            self.config.logger.warning(
                              'sleeping for %s, and then trying again',
                              60
                            )
                            self._responsive_sleep(60)
                            processor_iter = self._balanced_processor_iter()
                    # if the monitor starts misbehaving and not quitting after
                    # a SIGTERM or ^C, uncomment the following two line.  It
                    # will help diagnose the problem.
                    #except KeyboardInterrupt:
                        #self.config.logger.debug("inner detects quit")
                        #self.quit = True
                        #raise
                    except Exception:
                        self.config.logger.error(
                          'Unexpected exception while assigning jobs '
                          'to processors',
                          exc_info=True
                        )
                self.config.logger.info("end _standard_job_thread cycle")
                self._responsive_sleep(
                  self.config.job_manager.standard_loop_frequency
                )
        except Exception:
            self.config.logger.critical(
              'something is seriously wrong',
              exc_info=True
            )
            self.quit = True
            raise
        except (KeyboardInterrupt, SystemExit):
            #self.config.logger.debug("outer detects quit")
            self.quit = True
        finally:
            self.config.logger.debug("_standard_job_thread done.")

    #--------------------------------------------------------------------------
    def _get_priority_jobs_transaction(self, connection):
        """this method implements a single transaction that just returns a
        set of priority jobs."""
        priority_jobs_list = execute_query_fetchall(
          connection,
          "select * from priorityjobs"
        )
        return set(priority_jobs_list)

    #--------------------------------------------------------------------------
    def _prioritize_previously_enqueued_jobs_transaction(self, connection,
                                                         uuid):
        """priorty jobs come into the system at random times.  A given ooid
        may already be queued for processing when a priority request comes in
        for it.  To avoid repeating processing, a priority ooid is checked to
        see if it is already queued.  If it is, the processor already assigned
        to it is told to expedite processing.  This done just by entering the
        ooid into the processors private 'priority_jobs_XXX' table."""
        try:
            job_owner = single_value_sql(
              connection,
              "select owner from jobs where uuid = %s",
              (uuid,)
            )
        except SQLDidNotReturnSingleValue:
            return False
        priority_job_table_name = 'priority_jobs_%d' % job_owner
        self.config.logger.info(
          "priority job %s was already in the queue, assigned to %d",
          uuid,
          job_owner
        )
        try:
            # detect if the found job was assigned to a processor that was
            # dead by checking to see if the priority jobs table exists or
            # not.  If id doesn't exist, wait for the job to get reassigned
            # to a live processor.  It in the future, it may be better to
            # just reassign the job immediately.
            single_value_sql(  # return value intentionally ignored
              connection,
              "select 1 from pg_stat_user_tables where relname = %s",
              (priority_job_table_name,)
            )
        except SQLDidNotReturnSingleValue:
            self.config.logger.debug(
              "%s assigned to dead processor %d - "
              "wait for reassignment",
              uuid,
              job_owner
            )
            # likely that the job is assigned to a dead processor
            # skip processing it this time around - by next time
            # hopefully it will have been
            # re assigned to a live processor
            return False
        execute_no_results(
          connection,
          "insert into %s (uuid) values (%%s)" %
            priority_job_table_name,
          (uuid,)
        )
        execute_no_results(
          connection,
          "delete from priorityjobs where uuid = %s",
          (uuid,)
        )
        return True

    #--------------------------------------------------------------------------
    def _prioritize_previously_enqueued_jobs(self, priority_jobs_set):
        """this method checks to see if any priorty jobs are already queued
        for processing.  If so, a transaction is executed that will expedite
        processing."""
        # check for uuids already in the queue
        for uuid in list(priority_jobs_set):  # must use list copy - the set
                                              # gets changed
            self._quit_check()
            success = self.job_manager_transaction(
              self._prioritize_previously_enqueued_jobs_transaction,
              uuid
            )
            if success:
                priority_jobs_set.remove(uuid)

    #--------------------------------------------------------------------------
    def _prioritize_unqueued_jobs(self, priority_jobs_set):
        """this method takes priority jobs that where not already queued
        and queues them."""
        self.config.logger.debug("starting prioritize_unqueued_jobs")
        processor_iter = None
        for uuid in list(priority_jobs_set):  # must use list copy - the set
                                              # gets changed
            self.config.logger.debug("looking for %s", uuid)
            while True:
                self.config.logger.info("priority queuing %s", uuid)
                if not processor_iter:
                    self.config.logger.debug(
                      "about to get unbalanced_processor_iter"
                    )
                    processor_iter = self._unbalanced_processor_iter()
                    self.config.logger.debug(
                      "unbalancedJobScheduler successfully fetched"
                    )
                assigned_processor = self.job_manager_transaction(
                  self._queue_priorty_job_transaction,
                  uuid,
                  processor_iter
                )
                if assigned_processor is None:
                    self.config.logger.critical(
                      "can't seem to assign this job to a processor, are "
                      "processors running?"
                    )
                    self._responsive_sleep(10)
                    continue
                self.config.logger.info(
                  "%s assigned to %d",
                  uuid,
                  assigned_processor
                )
                self.job_manager_transaction(
                  execute_no_results,
                  "delete from priorityjobs where uuid = %s",
                  (uuid,)
                )
                priority_jobs_set.remove(uuid)
                break

    ##-------------------------------------------------------------------------
    #def remove_missing_priority_jobs(self, priority_jobs_set):
        ## we've failed to find the uuids anywhere
        #for uuid in priority_jobs_set:
            #self.quit_check()
            #self.config.logger.warning(
              #"priority job %s was never found",
              #uuid
            #)
            #self.job_manager_transaction(
              #execute_no_results,
              #"delete from priorityjobs where uuid = %s",
              #(uuid,)
            #)

    #--------------------------------------------------------------------------
    def _priority_job_thread(self):
        """this method is the main function for the 'priority_job_thread'.  It
        periodically polls the 'priorityjobs' table for priority ooids.  Each
        ooid is first checked to see if it already enqueued. If not, it
        queues them."""
        self.config.logger.info("start _priority_job_thread")
        try:
            while (True):
                self.config.logger.info("begin _priority_job_thread cycle")
                try:
                    self._quit_check()
                    priority_jobs_set = self.job_manager_transaction(
                      self._get_priority_jobs_transaction
                    )
                    if priority_jobs_set:
                        self.config.logger.debug(
                          "beginning search for priority jobs"
                        )
                        self._prioritize_previously_enqueued_jobs(
                          priority_jobs_set
                        )
                        self._prioritize_unqueued_jobs(priority_jobs_set)
                        #self.remove_missing_priority_jobs(priority_jobs_set)
                #except KeyboardInterrupt:
                    #self.config.logger.debug("inner detects quit")
                    #raise
                except Exception:
                    self.config.logger.error(
                      "Unexpected exception",
                      exc_info=True
                    )
                self.config.logger.info("end _priority_job_thread cycle")
                self._responsive_sleep(
                  self.config.job_manager.priority_loop_frequency
                )
        except (KeyboardInterrupt, SystemExit):
            #self.config.logger.debug("outer detects quit")
            self.quit = True
        except Exception:
            self.config.logger.critical(
              "something's gone horribly wrong",
              exc_info=True
            )
            self.quit = True
        finally:
            self.config.logger.info("priorityLoop done.")

    #--------------------------------------------------------------------------
    def main(self):
        """this function is run by the main thread.  It just starts the
        subordinate threads and then waits for them to complete."""
        standard_job_thread = threading.Thread(
          name="standard_job_thread",
          target=self._standard_job_thread
        )
        standard_job_thread.start()

        priority_job_thread = threading.Thread(
          name="priority_job_thread",
          target=self._priority_job_thread
        )
        priority_job_thread.start()

        job_cleanup_thread = threading.Thread(
          name="job_cleanup_thread",
          target=self._job_cleanup_thread
        )
        job_cleanup_thread.start()

        self.config.logger.debug("waiting to join.")
        self._responsive_join(job_cleanup_thread)
        self._responsive_join(priority_job_thread)
        self._responsive_join(standard_job_thread)


if __name__ == '__main__':
    main(MonitorApp)
