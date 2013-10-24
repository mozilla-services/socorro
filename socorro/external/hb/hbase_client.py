from socorro.app import generic_app

from configman import Namespace, RequiredConfig, ConfigurationManager
from configman.converters import class_converter

from socorro.external.hb.crashstorage import HBaseCrashStorage, \
                                             crash_id_to_row_id, \
                                             row_id_to_crash_id

import itertools
import pprint
import contextlib
import gzip
import sys
import json


_raises_exception = object()


class NotEnoughArguments(Exception):
    def __init__(self, arg):
        self.arg = arg


def expect_from_aggregation(required_config, name, i,
                            default=_raises_exception):
    def _closure(g, l, a):
        if len(a) < i + 1:
            if default is _raises_exception:
                raise NotEnoughArguments(name)
            return default
        return a[i]
    required_config.add_aggregation(name, _closure)


class _Command(RequiredConfig):
    required_config = Namespace()

    def __init__(self, app):
        self.app = app
        self.config = app.config
        self.storage = app.storage


class _CommandRequiringCrashID(_Command):
    required_config = Namespace()
    expect_from_aggregation(required_config, 'crash_id', 0)


class _CommandRequiringTable(_Command):
    required_config = Namespace()
    expect_from_aggregation(required_config, 'table', 0)


class _CommandRequiringTableRow(_CommandRequiringTable):
    required_config = Namespace()
    expect_from_aggregation(required_config, 'row_id', 1)


class _CommandRequiringScanParameters(_CommandRequiringTable):
    required_config = Namespace()
    expect_from_aggregation(required_config, 'prefix', 1)
    expect_from_aggregation(required_config, 'columns', 2)
    expect_from_aggregation(required_config, 'limit', 3)


class help(_Command):
    """Usage: help
    Get help on commands."""
    def run(self):
        self.app.config_manager.output_summary()

class get_raw_crash(_CommandRequiringCrashID):
    """Usage: get_raw_crash CRASH_ID
    Get the raw crash JSON data."""
    def run(self):
        pprint.pprint(self.storage.get_raw_crash(self.config.crash_id))


class get_raw_dumps(_CommandRequiringCrashID):
    """Usage: get_raw_dumps CRASH_ID
    Get information on the raw dumps for a crash."""
    def run(self):
        for name, dump in self.storage.get_raw_dumps(
            self.config.crash_id
        ).items():
            dump_name = "%s.%s.dump" % (self.config.crash_id, name)
            with open(dump_name, "w") as f:
                f.write(dump)
            print("%s: dump length = %s" % (name, len(dump)))


class get_processed(_CommandRequiringCrashID):
    """Usage: get_processed CRASH_ID
    Get the processed JSON for a crash"""
    def run(self):
        if self.config.json:
            print json.dumps(self.storage.get_processed(self.config.crash_id))
        else:
            pprint.pprint(self.storage.get_processed(self.config.crash_id))


class get_unredacted_processed(_CommandRequiringCrashID):
    """Usage: get_processed CRASH_ID
    Get the processed JSON for a crash"""
    def run(self):
        if self.config.json:
            print json.dumps(self.storage.get_unredacted_processed(
                self.config.crash_id
            ))
        else:
            pprint.pprint(self.storage.get_unredacted_processed(
                self.config.crash_id
            ))


class get_report_processing_state(_CommandRequiringCrashID):
    """Usage: get_report_processing_state CRASH_ID
    Get the report processing state for a crash."""
    def run(self):
        @self.storage._wrap_in_transaction
        def transaction(conn):
            pprint.pprint(self.storage._get_report_processing_state(
                conn,
                self.config.crash_id
            ))
        transaction()


class union_scan_with_prefix(_CommandRequiringScanParameters):
    """Usage: union_scan_with_prefix TABLE PREFIX COLUMNS [LIMIT]
    Do a union scan on a table using a given prefix."""
    def run(self):
        @self.storage._wrap_in_transaction
        def transaction(conn, limit=self.config.limit):
            for row in itertools.islice(
                self.storage._union_scan_with_prefix(
                    conn,
                    self.config.table,
                    self.config.prefix,
                    self.config.columns
                ),
            self.config.limit):
                pprint.pprint(row)
        transaction()


class merge_scan_with_prefix(_CommandRequiringScanParameters):
    """Usage: merge_scan_with_prefix TABLE PREFIX COLUMNS [LIMIT]
    Do a merge scan on a table using a given prefix."""
    def run(self):
        @self.storage._wrap_in_transaction
        def transaction(conn, limit=self.config.limit):
            for row in itertools.islice(
                self.storage._merge_scan_with_prefix(
                    conn,
                    self.config.table,
                    self.config.prefix,
                    self.config.columns
                ),
            self.config.limit):
                pprint.pprint(row)
        transaction()


class describe_table(_CommandRequiringTable):
    """Usage: describe_table TABLE
    Describe the details of a table in HBase."""
    def run(self):
        @self.storage._wrap_in_transaction
        def transaction(conn):
            pprint.pprint(conn.getColumnDescriptors(self.config.table))
        transaction()


class get_full_row(_CommandRequiringTableRow):
    """Usage: describe_table TABLE ROW_ID
    Pretty-print a row in HBase."""
    def run(self):
        @self.storage._wrap_in_transaction
        def transaction(conn):
            pprint.pprint(self.storage._make_row_nice(conn.getRow(
                self.config.table,
                self.config.row_id
            )[0]))
        transaction()


class export_processed_crashes_for_date(_Command):
    """Usage: export_processed_crashes_for_date DATE PATH
    Export all crashes for a given date to a path."""
    required_config = Namespace()
    expect_from_aggregation(required_config, 'date', 0)
    expect_from_aggregation(required_config, 'path', 1)

    def run(self):
        @self.storage._wrap_in_transaction
        def transaction(conn):
            for row in itertools.islice(
                self.storage._union_scan_with_prefix(conn,
                                                    'crash_reports',
                                                    self.config.date,
                                                    ['processed_data:json']),
                10
            ):
                crash_id = row_id_to_crash_id(row['_rowkey'])

                if row['processed_data:json']:
                    file_name = os.path.join(self.config.path,
                                             crash_id + '.jsonz')
                    with contextlib.closing(gzip.GzipFile(file_name,
                                                          'w',
                                                          9)) as f:
                        json.dump(row['processed_data:json'], f)
        transaction()


class HBaseClientConfigurationManager(ConfigurationManager):
    def output_summary(self, output_stream=sys.stdout, block_password=True):
        super(HBaseClientConfigurationManager, self).output_summary(
            output_stream,
            block_password
        )

        print >> output_stream, "Available commands:"

        for command in (var for var in globals().values()
                        if isinstance(var, type) and
                           issubclass(var, _Command) and
                           var.__name__[0] != '_'):

            print >> output_stream, '  ' + command.__name__
            print >> output_stream, '    ' + (command.__doc__ or
                                             '(undocumented)')
            print >> output_stream, ''


class HBaseClientApp(generic_app.App):
    app_name = "hbase_client.py"
    app_version = "0.1"
    app_description = __doc__

    required_config = Namespace()
    required_config.add_option(
        'hbase_crash_storage_class',
        default=HBaseCrashStorage,

        doc='the class responsible for proving an hbase connection',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'command',
        default=help,
        doc='command to use',
        from_string_converter=lambda s: class_converter(__name__ + '.' + s)
    )
    required_config.add_option(
        'json',
        default=False,
        short_form='j',
        doc='json output',
    )


    def main(self):
        self.storage = self.config.hbase_crash_storage_class(self.config)
        self.config.command(self).run()


if __name__ == '__main__':
    try:
        generic_app.main(HBaseClientApp,
                         config_manager_cls=HBaseClientConfigurationManager)
    except NotEnoughArguments as e:
        print >> sys.stderr, "ERROR: was expecting another argument: " + e.arg
        print >> sys.stderr, "Use the 'help' command to get help on commands."
