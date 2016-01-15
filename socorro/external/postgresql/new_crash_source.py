# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import timedelta

from configman import Namespace, RequiredConfig, class_converter

from socorro.lib.converters import (
    change_default,
)
from socorro.lib.datetimeutil import (
    utc_now,
    string_to_datetime,
)
from socorro.external.postgresql.dbapi2_util import execute_query_fetchall


#==============================================================================
class PGQueryNewCrashSource(RequiredConfig):
    """This class is an iterator that will yield a stream of crash_ids based
    on a query to the PG database."""
    required_config = Namespace()
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        'database_class',
        default=(
            'socorro.external.postgresql.connection_context'
            '.ConnectionContext'
        ),
        doc='the class responsible for connecting to Postgres',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        'crash_id_query',
        doc='sql to get a list of crash_ids',
        default="select 'some_id'",
        likely_to_be_changed=True,
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, name, quit_check_callback=None):
        self.database = config.database_class(
            config
        )
        self.transaction = config.transaction_executor_class(
            config,
            self.database,
            quit_check_callback=quit_check_callback
        )
        self.config = config
        self.name = name
        self.data = ()
        self.crash_id_query = config.crash_id_query

    #--------------------------------------------------------------------------
    def __iter__(self):
        crash_ids = self.transaction(
            execute_query_fetchall,
            self.crash_id_query,
            self.data
        )

        for a_crash_id in crash_ids:
            yield a_crash_id

    #--------------------------------------------------------------------------
    def close(self):
        self.database.close()

    #--------------------------------------------------------------------------
    new_crashes = __iter__

    #--------------------------------------------------------------------------
    def __call__(self):
        return self.__iter__()


#==============================================================================
class PGPVNewCrashSource(PGQueryNewCrashSource):
    required_config = Namespace()
    required_config.crash_id_query = change_default(
        PGQueryNewCrashSource,
        'crash_id_query',
        "select uuid "
        "from reports_clean rc join product_versions pv "
        "    on rc.product_version_id = pv.product_version_id "
        "where "
        "%s <= date_processed and date_processed < %s "
        "and %s between pv.build_date and pv.sunset_date"
    )
    required_config.add_option(
        'date',
        doc="a date in the form YYYY-MM-DD",
        default=(utc_now() - timedelta(1)).date(),
        from_string_converter=string_to_datetime
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, name, quit_check_callback=None):
        super(PGPVNewCrashSource, self).__init__(
            config,
            name,
            quit_check_callback
        )
        self.data = (
            config.date,
            config.date + timedelta(1),  # add a day
            config.date
        )


#==============================================================================
class DBCrashStorageWrapperNewCrashSource(PGQueryNewCrashSource):
    """This class is both a crashstorage system and a new_crash_source
    iterator.  The base FTSApp classes ties the iteration of new crashes
    to the crashstorage system designed as the 'source'.  This class is
    appropriate for use in that case as a 'source'."""

    required_config = Namespace()
    required_config.namespace('implementation')
    required_config.implementation.add_option(
        'crashstorage_class',
        default='socorro.external.boto.crashstorage.BotoS3CrashStorage',
        doc='a class for a source of raw crashes',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, name=None, quit_check_callback=None):
        super(DBCrashStorageWrapperNewCrashSource, self).__init__(
            config,
            name=name,
            quit_check_callback=quit_check_callback
        )
        self._implementation = config.implementation.crashstorage_class(
            config.implementation,
            quit_check_callback
        )

    #--------------------------------------------------------------------------
    def close(self):
        super(DBCrashStorageWrapperNewCrashSource, self).close()
        self._implementation.close()

    #--------------------------------------------------------------------------
    def __getattr__(self, method):
        def inner(*args, **kwargs):
            return getattr(self._implementation, method)(*args, **kwargs)
        return inner
