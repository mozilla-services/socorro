from socorro.app import generic_app
from configman import Namespace

from socorro.external.hb.crashstorage import HBaseCrashStorage, \
                                             crash_id_to_row_id, \
                                             row_id_to_crash_id

import itertools
import pprint
import argparse
import contextlib
import gzip

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help='sub-command help')

def action(f):
    f.parser = subparsers.add_parser(f.__name__, help=f.__doc__)
    f.parser.set_defaults(action=f)

    f.parser_args = {}

    args = list(f.func_code.co_varnames[:f.func_code.co_argcount][1:])
    optionals = []

    if f.func_defaults is not None:
        for _ in xrange(len(f.func_defaults)):
            optionals.append(args.pop())
    optionals.reverse()

    for arg_name in args:
        f.parser_args[arg_name] = f.parser.add_argument(arg_name)

    for arg_name, default in zip(optionals, f.func_defaults or []):
        f.parser_args[arg_name] = f.parser.add_argument(arg_name,
                                                        default=default,
                                                        nargs='?')

    return f


def annotate(param, **items):
    def _decorator(f):
        for k, v in items.iteritems():
            setattr(f.parser_args[param], k, v)
        return f
    return _decorator


@action
def get_raw_crash(storage, crash_id):
    """get the raw crash json data"""
    pprint.pprint(storage.get_raw_crash(crash_id))


@action
def get_raw_dumps(storage, crash_id):
    """get information on the raw dumps for a crash"""
    for name, dump in storage.get_raw_dumps(crash_id).items():
        print("%s: dump length = %s" % (name, len(dump)))


@action
def get_processed(storage, crash_id):
    """get the processed json for a crash"""
    pprint.pprint(storage.get_processed(crash_id))


@action
def get_report_processing_state(storage, crash_id):
    """get the report processing state for a crash"""
    @storage._wrap_in_transaction
    def transaction(conn):
        pprint.pprint(storage._get_report_processing_state(conn, crash_id))
    transaction()


@annotate('limit', type=int)
@annotate('columns', type=lambda x: x.split(','))
@action
def union_scan_with_prefix(storage, table, prefix, columns, limit=10):
    """do a union scan on a table using a given prefix"""
    @storage._wrap_in_transaction
    def transaction(conn, limit=limit):
        for row in itertools.islice(storage._union_scan_with_prefix(conn,
                                                                    table,
                                                                    prefix,
                                                                    columns),
                                    limit):
            pprint.pprint(row)
    transaction()


@annotate('limit', type=int)
@annotate('columns', type=lambda x: x.split(','))
@action
def merge_scan_with_prefix(storage, table, prefix, columns, limit=10):
    """do a merge scan on a table using a given prefix"""
    @storage._wrap_in_transaction
    def transaction(conn, limit=limit):
        for row in itertools.islice(storage._merge_scan_with_prefix(conn,
                                                                    table,
                                                                    prefix,
                                                                    columns),
                                    limit):
            pprint.pprint(row)
    transaction()


@action
def describe_table(storage, table):
    @storage._wrap_in_transaction
    def transaction(conn):
        pprint.pprint(conn.getColumnDescriptors(table))
    transaction()


@action
def get_full_row(storage, table, row_id):
    @storage._wrap_in_transaction
    def transaction(conn):
        pprint.pprint(storage._make_row_nice(conn.getRow(table, row_id)[0]))
    transaction()


@action
def export_processed_crashes_for_date(storage, date, path):
    @storage._wrap_in_transaction
    def transaction(conn):
        for row in itertools.islice(
            storage._union_scan_with_prefix(conn,
                                            'crash_reports',
                                            date,
                                            ['processed_data:json']), 10):

            crash_id = row_id_to_crash_id(row['_rowkey'])

            if row['processed_data:json']:
                file_name = os.path.join(path, crash_id + '.jsonz')
                with contextlib.closing(gzip.GzipFile(file_name, 'w', 9)) as f:
                    json.dump(row['processed_data:json'], f)
    transaction()

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
