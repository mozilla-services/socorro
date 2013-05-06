# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from datetime import datetime
from collections import defaultdict

from configman import Namespace, RequiredConfig
from configman.converters import class_converter, timedelta_converter

from socorro.lib.datetimeutil import utc_now, UTC
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.database.transaction_executor import TransactionExecutor
from socorro.external.postgresql.dbapi2_util import (
  single_value_sql,
  execute_no_results,
  SQLDidNotReturnSingleValue
)


#==============================================================================
class RegistrationError(Exception):
    """the exception used when there is a problem within registration"""
    pass


#==============================================================================
class ProcessorAppNullRegistrationClient(RequiredConfig):
    """the registrar isn't needed when the monitor is not in use.  This class
    will stub out the registration system of the processor."""

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        """constructor for a registration object that does nothing at all"""
        hostname = os.uname()[1].replace('.', '_')
        self.processor_name = "%s_%d" % (
            hostname,
            os.getpid()
        )


    #--------------------------------------------------------------------------
    def checkin(self):
        pass

    #--------------------------------------------------------------------------
    def unregister(self):
        pass


#==============================================================================
class ProcessorAppRegistrationClient(RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
      'database_class',
      doc="the class of the registrar's database",
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
      'processor_id',
      doc='the id number for the processor (must already exist) (0 for create '
          'new Id, "auto" for autodetection, "host" for same host, '
          '"forcehost" for hostile take over)',
      default='forcehost'
    )
    required_config.add_option(
      'check_in_frequency',
      doc='how often the processor is required to reregister (hh:mm:ss)',
      default="00:05:00",
      from_string_converter=timedelta_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        """constructor for a registration object.

        Parameters:
            config - dict-like object containing key/value pairs.  the keys
                     are accessible via dot syntax: config.some_key.
                     From the config, this classes uses the keys:
                     logger - a logger object"""
        self.config = config

        self.database = config.database_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            self.database,
            quit_check_callback=quit_check_callback
        )
        self.last_checkin_ts = datetime(1999, 1, 1, tzinfo=UTC)
        self.processor_id = None
        self.processor_name = 'unknown'
        self._registration()

    #--------------------------------------------------------------------------
    def _registration(self):
        """This function accomplishes the actual registration in the table
        inside Postgres.  There are four types of registrations, selected
        by the value of the configuration parameter 'processor_id'.
            assume_new_identity - when processor_id is 0.  The processor should
                                  just register in the table as a brand new
                                  processor.  A new id will be assigned to this
                                  processor.
            assume_specific_identity - when processor_id is a non-zero integer.
                                       the processor should take over for a
                                       defunct processor with a specific ID.
            assume_any_identity - when the processor_id is "auto".  The
                                  processor should look for any other
                                  registered processor that has died and take
                                  over for it.
            assume_identity_by_host - when the processor_id is "host".
                                      the processor should look for another
                                      registered processor that has a name
                                      indicating that it came from the same
                                      host, and then take over for it.

        Each of the aforementioned registration methods is implemented by
        a function of the same name.  These are called via a dispatch table
        called 'dispatch_table'.  Since they are all called this way, they
        must all have the same parameters, hense a fat interface.  Not all
        parameters will be used by all methods."""

        requested_id = self._requested_processor_id(
          self.config.processor_id
        )
        hostname = os.uname()[1].replace('.', '_')
        self.processor_name = "%s_%d" % (
            hostname,
            os.getpid()
        )

        threshold = self.transaction(
          single_value_sql,
          "select now() - interval %s",
          (self.config.check_in_frequency,)
        )

        dispatch_table = defaultdict(
          lambda: self._assume_specific_identity,
          {'auto': self._assume_any_identity,
           'host': self._assume_identity_by_host,
           'forcehost': self._force_assume_identity_by_host,
           0: self._assume_new_identity}
        )

        self.config.logger.info("registering with 'processors' table")
        try:
            self.processor_id = self.transaction(
              dispatch_table[requested_id],
              threshold,
              hostname,
              requested_id
            )
        except Exception:
            self.config.logger.critical('unable to complete registration',
                                 exc_info=True)
            raise

    #--------------------------------------------------------------------------
    def _assume_identity_by_host(self, connection, threshold, hostname,
                                req_id):
        """This function implements the case where a newly registering
        processor wants to take over for a dead processor with the same host
        name as the registering processor.

        Parameters:
            connection - a connection object
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
        self.config.logger.debug(
          "looking for a dead processor for host %s",
          hostname
        )
        try:
            sql = ("select id from processors"
                   " where lastseendatetime < %s"
                   " and name like %s limit 1")
            hostname_phrase = hostname + '%'
            processor_id = single_value_sql(
              connection,
              sql,
              (threshold, hostname_phrase)
            )
            self.config.logger.info(
              "will step in for processor %s",
              processor_id
            )
            # a dead processor for this host was found
            self._take_over_dead_processor(connection, processor_id)
            return processor_id
        except SQLDidNotReturnSingleValue:
            # no dead processor was found for this host, is there already
            # a live processor for it?
            self.config.logger.debug("no dead processor found for host, %s",
                              hostname)
            try:
                sql = ("select id from processors"
                       " where name like '%s%%'" % hostname)
                self.processor_id = single_value_sql(connection, sql)
                message = ('a live processor already exists for host %s' %
                           hostname)
                # there was a live processor found for this host, we cannot
                # complete registration
                raise RegistrationError(message)
            except SQLDidNotReturnSingleValue:
                # there was no processor for this host was found, make new one
                return self._assume_new_identity(connection, threshold,
                                                hostname, req_id)

    #--------------------------------------------------------------------------
    def _force_assume_identity_by_host(self, connection, threshold, hostname,
                                       req_id):
        """This function implements the case where a newly registering
        processor wants to take over for a processor with the same host
        name as the registering processor.  This is the case where the
        existing processor is likely dead but didn't manage to halt cleanly.

        Parameters:
            connection - a connection object
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
        self.config.logger.debug(
          "looking for a processor for host %s",
          hostname
        )
        try:
            sql = ("select id from processors"
                   " where name like %s limit 1")
            hostname_phrase = hostname + '%'
            processor_id = single_value_sql(
              connection,
              sql,
              (hostname_phrase,)
            )
            self.config.logger.info(
              "will take over processor %s",
              processor_id
            )
            # a processor for this host was found
            self._take_over_dead_processor(connection, processor_id)
            return processor_id
        except SQLDidNotReturnSingleValue:
            return self._assume_new_identity(connection, threshold,
                                             hostname, req_id)

    #--------------------------------------------------------------------------
    def _assume_any_identity(self, connection, threshold, hostname, req_id):
        """This function implements the case where we're interested in taking
        over for any dead processor regardless of what host it was running on.

        Parameters:
            connection - a connection object
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
        self.config.logger.debug("looking for any dead processor")
        try:
            sql = ("select id from processors"
                   " where lastseendatetime < %s limit 1")
            processor_id = single_value_sql(connection,
                                            sql,
                                            (threshold,))
            self.config.logger.info(
              "will step in for processor %s",
              processor_id
            )
            self._take_over_dead_processor(connection, processor_id)
            return processor_id
        except SQLDidNotReturnSingleValue:
            self.config.logger.debug(
              "no dead processor found, registering as new"
            )
            return self._assume_new_identity(connection, threshold, hostname,
                                            req_id)

    #--------------------------------------------------------------------------
    def _assume_specific_identity(self, connection, threshold, hostname,
                                 req_id):
        """This function implements the case where we want the processor to
        take over for a specific existing but dead processor without regard
        to what host the dead processor was running on.  If the dead processor
        was not found, or the processor was not really dead, the function will
        raise a RegistrationError and decline to register the new processor.

        Parameters:
            connection - a connection object
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

        self.config.logger.debug("looking for a specific dead processor")
        try:
            check_sql = ("select id from processors "
                         "where lastSeenDateTime < %s "
                         "and id = %s")
            processor_id = single_value_sql(connection,
                                            check_sql,
                                            (threshold, req_id))
            self.config.logger.info(
              "stepping in for processor %s",
              processor_id
            )
            self._take_over_dead_processor(connection, processor_id)
            return processor_id
        except SQLDidNotReturnSingleValue:
            raise RegistrationError("%s doesn't exist or is not dead" %
                                    req_id)

    #--------------------------------------------------------------------------
    def _assume_new_identity(self, connection, threshold, hostname, req_id):
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
        self.config.logger.debug("becoming a new processor")
        return single_value_sql(connection,
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
    def _take_over_dead_processor(self, connection, req_id):
        """This function implement the method to take over for a dead
        processor within the 'processors' table in the database.

        Parameters:
            connection - a database connection object used to talk to the
                         database
            req_id - the id of the processor that is to be taken over.  This
                     is the 'id' column of the 'processors' table."""
        cursor = connection.cursor()
        self.config.logger.debug("trying to take over for a dead processor")
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
    def _requested_processor_id(requested_id):
        """This method makes sure that the configuration parameter
        'processorID' is in the proper form.  If it is an integer, it is cast
        into the integer type.  If it is a string, it is ensured to be one
        of the acceptable values.

        Parameters:
            requested_id - the value is passed in from the 'processor_id'
                           configuration parameter.
        Returns:
            an integer or the the strings 'host' or 'auto'"""
        try:
            return int(requested_id)
        except ValueError:
            if requested_id in ('auto', 'host', 'forcehost'):
                return requested_id
            else:
                raise ValueError("'%s' is not a valid value" % requested_id)

    #--------------------------------------------------------------------------
    def checkin(self):
        """ a processor must keep its database registration current.  If a
        processor has not updated its record in the database in the interval
        specified in as self.config.check_in_frequency, the monitor
        will consider it to be expired.  The monitor will stop assigning jobs
        to it and reallocate its unfinished jobs to other processors.
        """
        tstamp = utc_now()
        if (self.last_checkin_ts + self.config.check_in_frequency
                                             < tstamp):
            self.config.logger.debug("updating processor registration")
            self.transaction(
              execute_no_results,
              "update processors set lastseendatetime = %s where id = %s",
              (tstamp, self.processor_id)
            )
            self.last_checkin_ts = tstamp

    #--------------------------------------------------------------------------
    def unregister(self):
        self.transaction.do_quit_check = False
        self.transaction(
          execute_no_results,
          "update processors set lastseendatetime = '1999-12-31'"
                  " where id = %s",
          (self.processor_id,)
        )
