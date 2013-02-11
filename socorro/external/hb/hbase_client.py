from socorro.app import generic_app
from configman import Namespace

from socorro.external.hb.crashstorage import HBaseCrashStorage, \
                                             crash_id_to_row_id

import itertools
import pprint
import argparse

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help='sub-command help')

def action(f):
    f.parser = subparsers.add_parser(f.__name__, help=f.__doc__)
    f.parser.set_defaults(action=f)
    return f


@action
def get_raw_crash(storage, crash_id):
    """get the raw crash json data"""
    pprint.pprint(storage.get_raw_crash(crash_id))
get_raw_crash.parser.add_argument('crash_id',
                                  help='crash id to look up')


@action
def get_raw_dumps(storage, crash_id):
    """get information on the raw dumps for a crash"""
    for name, dump in storage.get_raw_dumps(crash_id).items():
        print("%s: dump length = %s" % (name, len(dump)))
get_raw_dumps.parser.add_argument('crash_id',
                                  help='crash id to look up')


@action
def get_processed(storage, crash_id):
    """get the processed json for a crash"""
    pprint.pprint(storage.get_processed(crash_id))
get_processed.parser.add_argument('crash_id',
                                  help='crash id to look up')


@action
def get_report_processing_state(storage, crash_id):
    """get the report processing state for a crash"""
    @storage._run_in_transaction
    def transaction(conn):
        pprint.pprint(storage._get_report_processing_state(conn, crash_id))
get_report_processing_state.parser.add_argument('crash_id',
                                                help='crash id to look up')


@action
def union_scan_with_prefix(storage, table, prefix, columns, limit=None):
    """do a union scan on a table using a given prefix"""
    @storage._run_in_transaction
    def transaction(conn, limit=limit):
        if limit is None:
            limit = 10
        for row in itertools.islice(storage._union_scan_with_prefix(conn,
                                                                    table,
                                                                    prefix,
                                                                    columns),
                                    limit):
            pprint.pprint(row)
union_scan_with_prefix.parser.add_argument('table',
                                           help='scan table')
union_scan_with_prefix.parser.add_argument('prefix',
                                           help='scan prefix')
union_scan_with_prefix.parser.add_argument('columns',
                                           help='columns to use',
                                           type=lambda x: x.split(','))
union_scan_with_prefix.parser.add_argument('limit',
                                           help='query limit (default: 10)',
                                           default=10,
                                           nargs='?')


@action
def merge_scan_with_prefix(storage, table, prefix, columns, limit=None):
    """do a merge scan on a table using a given prefix"""
    @storage._run_in_transaction
    def transaction(conn, limit=limit):
        if limit is None:
            limit = 10
        for row in itertools.islice(storage._merge_scan_with_prefix(conn,
                                                                    table,
                                                                    prefix,
                                                                    columns),
                                    limit):
            pprint.pprint(row)
merge_scan_with_prefix.parser.add_argument('table',
                                           help='scan table')
merge_scan_with_prefix.parser.add_argument('prefix',
                                           help='scan prefix')
merge_scan_with_prefix.parser.add_argument('columns',
                                           help='columns to use',
                                           type=lambda x: x.split(','))
merge_scan_with_prefix.parser.add_argument('limit',
                                           help='query limit (default: 10)',
                                           default=10,
                                           nargs='?')


@action
def describe_table(storage, table):
    @storage._run_in_transaction
    def transaction(conn):
        pprint.pprint(conn.getColumnDescriptors(table))
describe_table.parser.add_argument('table',
                                   help='table to describe')


@action
def get_full_row(storage, table, row_id):
    @storage._run_in_transaction
    def transaction(conn):
        pprint.pprint(storage._make_row_nice(conn.getRow(table, row_id)[0]))
get_full_row.parser.add_argument('table',
                                 help='table to describe')
get_full_row.parser.add_argument('row_id',
                                 help='row to retrieve')


class MainApp(generic_app.App):
    app_name = "hbase_client.py"
    app_version = "0"
    app_description = """
HBase client utilities.

%s
Configman options follow. These should come before any sub-command.\
""" % parser.format_help()

    required_config = Namespace()
    required_config.add_option(
        'hbase_crash_storage_class',
        default=HBaseCrashStorage,
        doc='the class responsible for proving an hbase connection'
    )

    def main(self):
        storage = self.config.hbase_crash_storage_class(self.config)
        args = parser.parse_args()
        args.action(storage, **dict((k, v)
                                    for k, v in args.__dict__.items()
                                    if k != 'action'))

if __name__ == '__main__':
    generic_app.main(MainApp)
