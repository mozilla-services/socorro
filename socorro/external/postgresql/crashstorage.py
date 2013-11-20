# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import threading
import json

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound
)
from configman import (
    Namespace,
    class_converter
)
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.lib.datetimeutil import uuid_to_date
from socorro.external.postgresql.dbapi2_util import (
    SQLDidNotReturnSingleValue,
    single_value_sql,
    execute_no_results
)


#==============================================================================
class PostgreSQLCrashStorage(CrashStorageBase):
    """this implementation of crashstorage saves processed crashes to
    an instance of Postgresql.  It only saves certain key values to the
    partitioned reports table, therefore it is not a source for fetching
    complete processed reports and doesn't not implement any of the 'get'
    methods."""

    required_config = Namespace()

    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
             "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql'
    )
    required_config.add_option(
        'database_class',
        default=ConnectionContext,
        doc='the class responsible for connecting to Postgres',
        reference_value_from='resource.postgresql'
    )

    _reports_table_mappings = (
        # processed name, reports table name
        ("addons_checked", "addons_checked"),
        ("address", "address"),
        ("app_notes", "app_notes"),
        ("build", "build"),
        ("client_crash_date", "client_crash_date"),
        ("completeddatetime", "completed_datetime"),
        ("cpu_info", "cpu_info"),
        ("cpu_name", "cpu_name"),
        ("date_processed", "date_processed"),
        ("distributor", "distributor"),
        ("distributor_version", "distributor_version"),
        ("email", "email"),
        ("exploitability", "exploitability"),
        #("flash_process_dump", "flash_process_dump"),  # future
        ("flash_version", "flash_version"),
        ("hangid", "hangid"),
        ("install_age", "install_age"),
        ("last_crash", "last_crash"),
        ("os_name", "os_name"),
        ("os_version", "os_version"),
        ("processor_notes", "processor_notes"),
        ("process_type", "process_type"),
        ("product", "product"),
        ("productid", "productid"),
        ("reason", "reason"),
        ("release_channel", "release_channel"),
        ("signature", "signature"),
        ("startedDateTime", "started_datetime"),
        ("success", "success"),
        ("topmost_filenames", "topmost_filenames"),
        ("truncated", "truncated"),
        ("uptime", "uptime"),
        ("user_comments", "user_comments"),
        ("user_id", "user_id"),
        ("url", "url"),
        ("uuid", "uuid"),
        ("version", "version"),
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(PostgreSQLCrashStorage, self).__init__(
            config,
            quit_check_callback=quit_check_callback
        )
        self.database = config.database_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            self.database,
            quit_check_callback=quit_check_callback
        )

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """nota bene: this function does not save the dumps in PG, only
        the raw crash json is saved."""
        self.transaction(self._save_raw_crash_transaction, raw_crash, crash_id)

    #--------------------------------------------------------------------------
    def _save_raw_crash_transaction(self, connection, raw_crash, crash_id):
        raw_crash_table_name = (
          'raw_crashes_%s' % self._table_suffix_for_crash_id(crash_id)
        )
        insert_sql = """insert into %s (uuid, raw_crash, date_processed) values
                        (%%s, %%s, %%s)""" % raw_crash_table_name
        savepoint_name = threading.currentThread().getName().replace('-', '')
        value_list = (
            crash_id,
            json.dumps(raw_crash),
            raw_crash["submitted_timestamp"]
        )
        execute_no_results(connection, "savepoint %s" % savepoint_name)
        try:
            execute_no_results(connection, insert_sql, value_list)
            execute_no_results(
              connection,
              "release savepoint %s" % savepoint_name
            )
        except self.config.database_class.IntegrityError:
            # report already exists
            execute_no_results(
              connection,
              "rollback to savepoint %s" % savepoint_name
            )
            execute_no_results(
              connection,
              "release savepoint %s" % savepoint_name
            )
            execute_no_results(
              connection,
              "delete from %s where uuid = %%s" % raw_crash_table_name,
              (crash_id,)
            )
            execute_no_results(connection, insert_sql, value_list)

    #--------------------------------------------------------------------------
    def get_raw_crash(self, crash_id):
        """the default implementation of fetching a raw_crash

        parameters:
           crash_id - the id of a raw crash to fetch"""
        return self.transaction(
            self._get_raw_crash_transaction,
            crash_id
        )

    #--------------------------------------------------------------------------
    def _get_raw_crash_transaction(self, connection, crash_id):
        raw_crash_table_name = (
          'raw_crash_%s' % self._table_suffix_for_crash_id(crash_id)
        )
        fetch_sql = 'select raw_crash from %s where uuid = %ss' % \
                    raw_crash_table_name
        try:
            return single_value_sql(connection, fetch_sql, (crash_id,))
        except SQLDidNotReturnSingleValue:
            raise CrashIDNotFound(crash_id)

    #--------------------------------------------------------------------------
    def save_processed(self, processed_crash):
        self.transaction(self._save_processed_transaction, processed_crash)

    #--------------------------------------------------------------------------
    def _save_processed_transaction(self, connection, processesd_crash):
        report_id = self._save_processed_report(connection, processesd_crash)
        self._save_plugins(connection, processesd_crash, report_id)
        self._save_extensions(connection, processesd_crash, report_id)

    #--------------------------------------------------------------------------
    def _save_processed_report(self, connection, processed_crash):
        column_list = []
        placeholder_list = []
        value_list = []
        for pro_crash_name, report_name in self._reports_table_mappings:
            column_list.append(report_name)
            placeholder_list.append('%s')
            value_list.append(processed_crash[pro_crash_name])
        crash_id = processed_crash['uuid']
        reports_table_name = (
          'reports_%s' % self._table_suffix_for_crash_id(crash_id)
        )
        insert_sql = "insert into %s (%s) values (%s) returning id" % (
            reports_table_name,
            ', '.join(column_list),
            ', '.join(placeholder_list)
        )
        # we want to insert directly into the report table.  There is a
        # chance however that the record already exists.  If it does, then
        # the insert would fail and the connection fall into a "broken" state.
        # To avoid this, we set a savepoint to which we can roll back if the
        # record already exists - essentially a nested transaction.
        # We use the name of the executing thread as the savepoint name.
        # alternatively we could get a uuid.
        savepoint_name = threading.currentThread().getName().replace('-', '')
        execute_no_results(connection, "savepoint %s" % savepoint_name)
        try:
            report_id = single_value_sql(connection, insert_sql, value_list)
            execute_no_results(
              connection,
              "release savepoint %s" % savepoint_name
            )
        except self.config.database_class.IntegrityError:
            # report already exists
            execute_no_results(
              connection,
              "rollback to savepoint %s" % savepoint_name
            )
            execute_no_results(
              connection,
              "release savepoint %s" % savepoint_name
            )
            execute_no_results(
              connection,
              "delete from %s where uuid = %%s" % reports_table_name,
              (processed_crash.uuid,)
            )
            report_id = single_value_sql(connection, insert_sql, value_list)
        return report_id

    #--------------------------------------------------------------------------
    def _save_plugins(self, connection, processed_crash, report_id):
        """ Electrolysis Support - Optional - processed_crash may contain a
        ProcessType of plugin. In the future this value would be default,
        content, maybe even Jetpack... This indicates which process was the
        crashing process.
            plugin - When set to plugin, the jsonDocument MUST calso contain
                     PluginFilename, PluginName, and PluginVersion
        """
        process_type = processed_crash['process_type']
        if not process_type:
            return

        if process_type == "plugin":

            # Bug#543776 We actually will are relaxing the non-null policy...
            # a null filename, name, and version is OK. We'll use empty strings
            try:
                plugin_filename = processed_crash['PluginFilename']
                plugin_name = processed_crash['PluginName']
                plugin_version = processed_crash['PluginVersion']
            except KeyError, x:
                self.config.logger.error(
                    'the crash is missing a required field: %s', str(x)
                )
                return
            find_plugin_sql = ('select id from plugins '
                               'where filename = %s '
                               'and name = %s')
            try:
                plugin_id = single_value_sql(connection,
                                             find_plugin_sql,
                                             (plugin_filename,
                                              plugin_name))
            except SQLDidNotReturnSingleValue:
                insert_plugsins_sql = ("insert into plugins (filename, name) "
                                       "values (%s, %s) returning id")
                plugin_id = single_value_sql(connection,
                                             insert_plugsins_sql,
                                             (plugin_filename,
                                              plugin_name))
            crash_id = processed_crash['uuid']
            table_suffix = self._table_suffix_for_crash_id(crash_id)
            plugin_reports_table_name = 'plugins_reports_%s' % table_suffix
            plugins_reports_insert_sql = (
                'insert into %s '
                '    (report_id, plugin_id, date_processed, version) '
                'values '
                '    (%%s, %%s, %%s, %%s)' % plugin_reports_table_name
            )
            values_tuple = (report_id,
                            plugin_id,
                            processed_crash['date_processed'],
                            plugin_version)
            execute_no_results(connection,
                               plugins_reports_insert_sql,
                               values_tuple)

    #--------------------------------------------------------------------------
    def _save_extensions(self, connection, processed_crash, report_id):
        extensions = processed_crash['addons']
        crash_id = processed_crash['uuid']
        table_suffix = self._table_suffix_for_crash_id(crash_id)
        extensions_table_name = 'extensions_%s' % table_suffix
        extensions_insert_sql = (
          "insert into %s "
          "    (report_id, date_processed, extension_key, extension_id, "
          "     extension_version)"
          "values (%%s, %%s, %%s, %%s, %%s)" % extensions_table_name
        )
        for i, x in enumerate(extensions):
            try:
                execute_no_results(connection, extensions_insert_sql,
                                   (report_id,
                                    processed_crash['date_processed'],
                                    i,
                                    x[0][:100],
                                    x[1]))
            except IndexError:
                self.config.logger.warning(
                  '"%s" is deficient as a name and version for an addon',
                  str(x[0])
                )

    #--------------------------------------------------------------------------
    @staticmethod
    def _table_suffix_for_crash_id(crash_id):
        """given an crash_id, return the name of its storage table"""
        crash_id_date = uuid_to_date(crash_id)
        previous_monday_date = (
          crash_id_date + datetime.timedelta(days=-crash_id_date.weekday())
        )
        return '%4d%02d%02d' % (previous_monday_date.year,
                                previous_monday_date.month,
                                previous_monday_date.day)
