import contextlib
import urllib2

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    OOIDNotFoundException
)
from socorro.database.transaction_executor import TransactionExecutor
from socorro.external.hbase.hbase_client import ooid_to_row_id

from configman import Namespace


#==============================================================================
class ElasticSearchCrashStorage(CrashStorageBase):
    """this implementation of crashstorage doesn't actually send data directly
    to ES, but to the SSS (Socorro Search Service). In terms of a storage
    system, this is a most degenerate case.  It doesn't implement saving any-
    thing but processed crashes and even with that, only submites the OOID
    to SSS.  It is the responsibilty of SSS to fetch the processed crash data
    from HBase and forward that to HBase.
    """

    required_config = Namespace()
    required_config.add_option('transaction_executor_class',
                               default=TransactionExecutor,
                               doc='a class that will manage transactions')
    required_config.add_option('submission_url',
                               doc='a url to submit ooids for Elastic Search '
                               '(use %s in place of the ooid) '
                               '(leave blank to disable)',
                               default='')
    required_config.add_option('timeout',
                               doc='how long to wait in seconds for '
                                   'confirmation of a submission',
                               default=2)

    operational_exceptions = (
          urllib2.socket.timeout,
    )

    conditional_exceptions = ()

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(ElasticSearchCrashStorage, self).__init__(
            config,
            quit_check_callback
        )
        self.transaction = config.transaction_executor_class(
            config,
            self,
            quit_check_callback
        )

    #--------------------------------------------------------------------------
    def save_processed(self, processed_crash):
        try:
            # Why is the function specified as unbound?  The elastic search
            # crashstorage class serves as its own connection context object.
            # In otherwords, it has no actual connection class.  The
            # transaction executor passes a connection object as the first
            # paremeter to the function that it calls.  That means that it will
            # be passing the ElasticSearchCrashStorage instance as the self
            # parameter.  A bound function would already have that input
            # parameter and thus an exception would be raised. By using an
            # unbound function, we avoid this problem.
            self.transaction(
              ElasticSearchCrashStorage._submit_ooid_to_elastic_search,
              processed_crash['uuid']
            )
        except KeyError, x:
            if x == 'uuid':
                raise OOIDNotFoundException
            raise

    #--------------------------------------------------------------------------
    def _submit_ooid_to_elastic_search(self, ooid):
        if self.config.submission_url:
            dummy_form_data = {}
            row_id = ooid_to_row_id(ooid)
            url = self.config.submission_url % row_id
            request = urllib2.Request(url, dummy_form_data)
            try:
                urllib2.urlopen(request, timeout=self.config.timeout).read()
            except urllib2.socket.timeout:
                self.logger.critical('%s may not have been submitted to '
                                     'Elastic Search due to a timeout',
                                     ooid)
                raise
            except Exception:
                self.logger.critical('Submition to Elastic Search failed '
                                     'for %s',
                                     ooid,
                                     exc_info=True)
                raise

    #--------------------------------------------------------------------------
    def commit(self):
        """elastic search doen't support transactions so this is silently
        does nothing"""
        pass

    #--------------------------------------------------------------------------
    def rollback(self):
        """elastic search doen't support transactions so this is silently
        does nothing"""
        pass

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self):
        """this class will serve as its own context manager.  That enables it
        to use the transaction_executor class for retries"""
        yield self

    #--------------------------------------------------------------------------
    def in_transaction(self, dummy):
        """elastic search doesn't support transactions, so it is never in
        a transaction."""
        return False

    #--------------------------------------------------------------------------
    def is_operational_exception(self, msg):
        return False
