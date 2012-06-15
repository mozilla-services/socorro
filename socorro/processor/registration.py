import datetime as dt
import os
import collections as col

import socorro.database.database as sdb
import socorro.lib.ConfigurationManager as scm
import socorro.lib.util as sutil

from socorro.lib.datetimeutil import utc_now, UTC


#==============================================================================
class RegistrationError(Exception):
    """the exception used when there is a problem within registration"""
    pass


#==============================================================================
class ProcessorRegistrationAgent(object):
    """This class encapsulates the processor's registration system in Postgres.
    There exists a table in Posgres called 'processors'.  Each processor, when
    it comes online, adds an entry about itself in that table.  This allows
    the monitor to know of the processor.  The monitor will then assign jobs to
    the registered processor.

    Processors must periodically update their registrations to indicate that
    they are still alive.  The update interval is controlled by the
    configuration parameter 'processorCheckInTime', a timedelta object.  The
    table in Postgres has a column called 'lastseendatetime'.  If the value
    in that column plus the 'processorCheckInTime' is less than 'now', then
    the processor is considered to be dead."""

    NOW_SQL = "select now() - interval %s"

    #--------------------------------------------------------------------------
    def __init__(self, config, db_conn_source, now_func=utc_now,
                 os_module=os, sdb_module=sdb):
        """constructor for a registration object.

        Parameters:
            config - dict-like object containing key/value pairs.  the keys
                     are accessible via dot syntax: config.some_key.
                     From the config, this classes uses the keys:
                     logger - a logger object
            db_conn_source - a connection pool object from which this class
                             get database connections
            now_func - the function that this class will use to get the
                       current timestamp. In production, the default is fine.
                       In testing, it is useful to use a custom and  more
                       predictable function.
            os_module - a reference to a module that provides the same services
                        as the built in 'os' module.  For production, the
                        default is fine. For testing, it is useful to pass in a
                        mocked object of some sort.
            sdb_module - a reference to the module that provides the Socorro
                         database connection services.  The default is fine
                         for production, but during testing, it is useful to
                         pass in a mocked object."""
        self.config = config
        self.db_pool = db_conn_source
        self.last_checkin_ts = dt.datetime(1999, 1, 1, tzinfo=UTC)
        self.logger = config.logger
        self.now_func = now_func
        self.os_module = os_module
        self.sdb_module = sdb_module
        self.processor_id = None
        self.processor_name = 'unknown'
        self.registration()

    #--------------------------------------------------------------------------
    @sdb.db_transaction_retry_wrapper
    def registration(self):
        """This function accomplishes the actual registration in the table
        inside Postgres.  There are four types of registrations, selected
        by the value of the configuration parameter 'processorId'.
            assume_new_identity - when processorId is 0.  The processor should
                                  just register in the table as a brand new
                                  processor.  A new id will be assigned to this
                                  processor.
            assume_specific_identity - when processorId is a non-zero integer.
                                       the processor should take over for a
                                       defunct processor with a specific ID.
            assume_any_identity - when the processorId is "auto".  The
                                  processor should look for any other
                                  registered processor that has died and take
                                  over for it.
            assume_identity_by_host - when the processorId is "host".
                                      the processor should look for another
                                      registered processor that has a name
                                      indicating that it came from the same
                                      host, and then take over for it.

        Each of the aforementioned registration methods is implemented by
        a function of the same name.  These are called via a dispatch table
        called 'dispatch_table'.  Since they are all called this way, they
        must all have the same parameters, hense a fat interface.  Not all
        parameters will be used by all methods."""
        self.logger.info("connecting to database")
        db_conn, db_cur = self.db_pool.connectionCursorPair()

        requested_id = self.requested_processor_id(self.config.processorId)
        hostname = self.os_module.uname()[1]
        self.processor_name = "%s_%d" % (hostname, self.os_module.getpid())
        threshold = self.sdb_module.singleValueSql(db_cur,
                                            self.NOW_SQL,
                                            (self.config.processorCheckInTime,)
                                            )
        dispatch_table = col.defaultdict(
            lambda: self.assume_specific_identity,
            {'auto': self.assume_any_identity,
             'host': self.assume_identity_by_host,
             0: self.assume_new_identity}
            )

        self.logger.info("registering with 'processors' table")
        try:
            self.processor_id = dispatch_table[requested_id](db_cur,
                                                            threshold,
                                                            hostname,
                                                            requested_id)
            db_conn.commit()
        except sdb.exceptions_eligible_for_retry:
            raise
        except Exception:
            db_conn.rollback()
            self.logger.critical('unable to complete registration')
            sutil.reportExceptionAndAbort(self.logger)

    #--------------------------------------------------------------------------
    def assume_identity_by_host(self, cursor, threshold, hostname, req_id):
        """This function implements the case where a newly registering
        processor wants to take over for a dead processor with the same host
        name as the registering processor.

        Parameters:
            cursor - a cursor object
            threshold - a datetime instance that represents an absolute date
                        made from the current datetime minus the timedelta
                        that defines how often a processor must update its
                        registration.  If the threshold is greater than the
                        'lastseendatetime' of a registered processor, that
                        processor is considered dead.
            hostname - the name of the host of the registering processor.
            req_id - not used by this method, but present to meet the required
                     api for a registration method.
        Returns:
            an integer representing the new id of the newly registered
            processor."""
        self.logger.debug("looking for a dead processor for host %s", hostname)
        try:
            sql = ("select id from processors"
                   " where lastseendatetime < %s"
                   " and name like %s limit 1")
            hostname_phrase = hostname + '%'
            processor_id = self.sdb_module.singleValueSql(cursor,
                                                          sql,
                                                          (threshold,
                                                           hostname_phrase))
            self.logger.info("will step in for processor %d", processor_id)
            # a dead processor for this host was found
            self.take_over_dead_processor(cursor, processor_id)
            return processor_id
        except sdb.SQLDidNotReturnSingleValue:
            # no dead processor was found for this host, is there already
            # a live processor for it?
            self.logger.debug("no dead processor found for host, %s",
                              hostname)
            try:
                sql = ("select id from processors"
                       " where name like '%s%%'" % hostname)
                self.processor_id = self.sdb_module.singleValueSql(cursor,
                                                                   sql)
                message = ('a live processor already exists for host %s' %
                           hostname)
                # there was a live processor found for this host, we cannot
                # complete registration
                raise RegistrationError(message)
            except sdb.SQLDidNotReturnSingleValue:
                # there was no processor for this host was found, make new one
                return self.assume_new_identity(cursor, threshold,
                                                hostname, req_id)

    #--------------------------------------------------------------------------
    def assume_any_identity(self, cursor, threshold, hostname, req_id):
        """This function implements the case where we're interested in taking
        over for any dead processor regardless of what host it was running on.

        Parameters:
            cursor - a cursor object
            threshold - a datetime instance that represents an absolute date
                        made from the current datetime minus the timedelta
                        that defines how often a processor must update its
                        registration.  If the threshold is greater than the
                        'lastseendatetime' of a registered processor, that
                        processor is considered dead.
            hostname - the name of the host of the registering processor.
                       not used by the method, but present to meet the
                       required api for a registration method.
            req_id - not used by this method, but present to meet the required
                     api for a registration method.
        Returns:
            an integer representing the new id of the newly registered
            processor."""
        self.logger.debug("looking for any dead processor")
        try:
            sql = ("select id from processors"
                   " where lastseendatetime < %s limit 1")
            processor_id = self.sdb_module.singleValueSql(cursor,
                                                          sql,
                                                          (threshold,))
            self.logger.info("will step in for processor %d", processor_id)
            self.take_over_dead_processor(cursor, processor_id)
            return processor_id
        except sdb.SQLDidNotReturnSingleValue:
            self.logger.debug("no dead processor found, registering as new")
            return self.assume_new_identity(cursor, threshold, hostname,
                                            req_id)

    #--------------------------------------------------------------------------
    def assume_specific_identity(self, cursor, threshold, hostname, id_req):
        """This function implements the case where we want the processor to
        take over for a specific existing but dead processor without regard
        to what host the dead processor was running on.  If the dead processor
        was not found, or the processor was not really dead, the function will
        raise a RegistrationError and decline to register the new processor.

        Parameters:
            cursor - a cursor object
            threshold - a datetime instance that represents an absolute date
                        made from the current datetime minus the timedelta
                        that defines how often a processor must update its
                        registration.  If the threshold is greater than the
                        'lastseendatetime' of a registered processor, that
                        processor is considered dead.
            hostname - the name of the host of the registering processor.
                       not used by the method, but present to meet the
                       required api for a registration method.
            req_id - an integer representing the 'id' (from the 'id' column of
                     'processors' database table) of the allegedly dead
                     processor.
        Returns:
            an integer representing the new id of the newly registered
            processor."""

        self.logger.debug("looking for a specific dead processor")
        try:
            check_sql = ("select id from processors "
                         "where lastSeenDateTime < %s "
                         "and id = %s")
            processor_id = self.sdb_module.singleValueSql(cursor,
                                                          check_sql,
                                                          (threshold, id_req))
            self.logger.info("stepping in for processor %d", processor_id)
            self.take_over_dead_processor(cursor, processor_id)
            return processor_id
        except sdb.SQLDidNotReturnSingleValue:
            raise RegistrationError("%d doesn't exist or is not dead" %
                                    id_req)

    #--------------------------------------------------------------------------
    def assume_new_identity(self, cursor, threshold, hostname, req_id):
        """This function implements the method of registering a brand new
        processor.  It will cause a new row to be entered into the 'processors'
        table within the database.

        Parameters:
            cursor - a cursor object
            threshold - not used by this method, but present to meet the
                        required api for a registration method.
            hostname - the name of the host of the registering processor.
                       not used by the method, but present to meet the
                       required api for a registration method.
            req_id - not used by this method, but present to meet the required
                     api for a registration method.
        Returns:
            an integer representing the new id of the newly registered
            processor."""
        self.logger.debug("becoming a new processor")
        return self.sdb_module.singleValueSql(cursor,
                                              "insert into processors"
                                              "    (id,"
                                              "     name,"
                                              "     startdatetime,"
                                              "     lastseendatetime) "
                                              "values"
                                              "    (default,"
                                              "     %s,"
                                              "     now(),"
                                              "     now()) "
                                              "returning id",
                                              (self.processor_name,))

    #--------------------------------------------------------------------------
    def take_over_dead_processor(self, cursor, req_id):
        """This function implement the method to take over for a dead
        processor within the 'processors' table in the database.

        Parameters:
            cursor - a database cursor object used to talk to the database
            req_id - the id of the processor that is to be taken over.  This
                     is the 'id' column of the 'processors' table."""
        self.logger.debug("taking over a dead processor")
        cursor.execute("update processors set name = %s, "
                       "startdatetime = now(), lastseendatetime = now()"
                       " where id = %s",
                       (self.processor_name, req_id))
        cursor.execute("update jobs set"
                       "    starteddatetime = NULL,"
                       "    completeddatetime = NULL,"
                       "    success = NULL "
                       "where"
                       "    owner = %s", (req_id, ))

    #--------------------------------------------------------------------------
    @staticmethod
    def requested_processor_id(requested_id):
        """This method makes sure that the configuration parameter
        'processorID' is in the proper form.  If it is an integer, it is cast
        into the integer type.  If it is a string, it is ensured to be one
        of the acceptable values.

        Parameters:
            requested_id - the value is passed in from the 'processorId'
                           configuration parameter.
        Returns:
            an integer or the the strings 'host' or 'auto'"""
        try:
            return int(requested_id)
        except ValueError:
            if requested_id in ('auto', 'host'):
                return requested_id
            else:
                raise scm.OptionError("'%s' is not a valid value"
                                      % requested_id)

    #--------------------------------------------------------------------------
    @sdb.db_transaction_retry_wrapper
    def checkin(self):
        """ a processor must keep its database registration current.  If a
        processor has not updated its record in the database in the interval
        specified in as self.config.processorCheckInTime, the monitor will
        consider it to be expired.  The monitor will stop assigning jobs to it
        and reallocate its unfinished jobs to other processors.
        """
        if (self.last_checkin_ts + self.config.processorCheckInFrequency
                                             < self.now_func()):
            self.logger.debug("updating 'processor' table registration")
            tstamp = self.now_func()
            db_conn, db_cur = self.db_pool.connectionCursorPair()
            db_cur.execute("update processors set lastseendatetime = %s "
                           "where id = %s", (tstamp, self.processor_id))
            db_conn.commit()
            self.last_checkin_ts = self.now_func()
