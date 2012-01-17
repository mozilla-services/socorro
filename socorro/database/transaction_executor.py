import time
from configman.config_manager import RequiredConfig
from configman import Namespace

from socorro.external.postgresql.transactional import Postgres


#------------------------------------------------------------------------------
def transaction_factory(config, local_config, args):
    """instantiate a transaction object that will create database
    connections

    This function will be associated with an Aggregation object.  It will
    look at the value of the 'database' option which is a reference to one
    of Postgres or PostgresPooled from above.  This function will
    instantiate the class
    """
    print "CONFIG"
    print repr(config)
    print config.keys()
    print "LOCAL_CONFIG"
    print repr(local_config)
    print local_config.keys()
    print "local_config.database_class"
    print repr(local_config.database_class)
    print
    return local_config.database_class(config, local_config)


#==============================================================================
class TransactionExecutor(RequiredConfig):
    required_config = Namespace()
    # setup the option that will specify which database connection/transaction
    # factory will be used.  Config man will query the class for additional
    # config options for the database connection parameters.
    required_config.add_option('database_class',
                               default=Postgres,
                               doc='the database connection source')
    # this Aggregation will actually instantiate the class in the preceding
    # option called 'database'.  Once instantiated, it will be available as
    # 'db_transaction'.  It will then be used as a source of database
    # connections cloaked as a context.
    required_config.add_aggregation(
        name='db_transaction',
        function=transaction_factory)

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config

    #--------------------------------------------------------------------------
    def do_transaction(self, function, *args, **kwargs):
        """execute a function within the context of a transaction"""
        with self.config.db_transaction() as trans:
            function(trans, *args, **kwargs)


#==============================================================================
class TransactionExecutorWithBackoff(TransactionExecutor):
    # back off times
    required_config = Namespace()
    required_config.add_option('backoff_delays',
                               default=[2, 4, 6, 10, 15],
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
                print '%s: %dsec of %dsec' % (wait_reason,
                                              x,
                                              seconds)
            time.sleep(1.0)

    #--------------------------------------------------------------------------
    def do_transaction(self, function, *args, **kwargs):
        """execute a function within the context of a transaction"""
        for wait_in_seconds in self.backoff_generator():
            try:
                with self.config.db_transaction() as trans:
                    function(trans, *args, **kwargs)
                    trans.commit()
                    break
            except self.config.db_transaction.operational_exceptions:
                pass
            print ('failure in transaction - retry in %s seconds' %
                   wait_in_seconds)
            self.responsive_sleep(wait_in_seconds,
                                  "waiting for retry after failure in "
                                  "transaction")
