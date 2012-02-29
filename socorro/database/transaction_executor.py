import time
import psycopg2.extensions
from configman.config_manager import RequiredConfig
from configman import Namespace

from socorro.external.postgresql.connection_context import ConnectionContext


#------------------------------------------------------------------------------
def connection_context_factory(config, local_config, args):
    """instantiate a transaction object that will create database
    connections

    This function will be associated with an Aggregation object.  It will
    look at the value of the 'database' option which is a reference to one
    of Postgres or PostgresPooled from above.  This function will
    instantiate the class
    """
    return local_config.database_class(config, local_config)


#==============================================================================
class TransactionExecutor(RequiredConfig):
    required_config = Namespace()

    # setup the option that will specify which database connector
    # will be used.
    required_config.add_option('database_class',
                               default=ConnectionContext,
                               doc='the database connection source')

    # add an aggregator whose function will set up the database_class above
    required_config.add_aggregation(
        name='db_connection_context',
        function=connection_context_factory)

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config

    #--------------------------------------------------------------------------
    def __call__(self, function, *args, **kwargs):
        """execute a function within the context of a transaction"""
        result = None
        with self.config.db_connection_context() as connection:
            try:
                function(connection, *args, **kwargs)
                connection.commit()
            except:
                if connection.get_transaction_status() == \
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS:
                    connection.rollback()
                self.config.logger.error(
                  'Exception raised during transaction',
                  exc_info=True)
                raise


#==============================================================================
class TransactionExecutorWithBackoff(TransactionExecutor):
    # back off times
    required_config = Namespace()
    required_config.add_option('backoff_delays',
                               default=[10, 30, 60, 120, 300],
                               doc='delays in seconds between retries',
                               from_string_converter=eval)
    # wait_log_interval
    required_config.add_option('wait_log_interval',
                               default=1,
                               doc='seconds between log during retries')

    #--------------------------------------------------------------------------
    def backoff_generator(self):
        """Generate a series of integers used for the length of the sleep
        between retries.  It produces after exhausting the list, it repeats
        the last value from the list forever.  This generator will never raise
        the StopIteration exception."""
        for x in self.config.backoff_delays:
            yield x
        while True:
            yield self.config.backoff_delays[-1]

    #--------------------------------------------------------------------------
    def responsive_sleep(self, seconds, wait_reason=''):
        """Sleep for the specified number of seconds, logging every
        'wait_log_interval' seconds with progress info."""
        for x in xrange(int(seconds)):
            if (self.config.wait_log_interval and
                not x % self.config.wait_log_interval):
                self.config.logger.debug(
                  '%s: %dsec of %dsec' % (wait_reason, x, seconds))
            time.sleep(1.0)

    #--------------------------------------------------------------------------
    def __call__(self, function, *args, **kwargs):
        """execute a function within the context of a transaction"""
        result = None
        connection_context = self.config.db_connection_context
        for wait_in_seconds in self.backoff_generator():
            try:
                # connection_context is an instance of a
                # wrapper class on the actual connection driver
                with connection_context() as connection:
                    try:
                        function(connection, *args, **kwargs)
                        connection.commit()
                        break
                    except:
                        if connection.get_transaction_status() == \
                          psycopg2.extensions.TRANSACTION_STATUS_INTRANS:
                            connection.rollback()
                        raise
            #except psycopg2.ProgrammingError, msg:
            except connection_context.conditional_exceptions, msg:
                if not connection_context.is_operational_exception(msg):
                    raise

                self.config.logger.warning(
                  'Exceptional database ProgrammingError exception',
                  exc_info=True)

            except connection_context.operational_exceptions:
                self.config.logger.warning(
                  'Database exception',
                  exc_info=True)
            self.config.logger.debug(
              'retry in %s seconds' % wait_in_seconds
            )
            self.responsive_sleep(
              wait_in_seconds,
              'waiting for retry after failure in transaction'
            )
