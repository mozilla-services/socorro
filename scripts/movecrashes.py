#!/usr/bin/env python

"""Export crash reports data from a PostgreSQL database or import crash reports
data into an ElasticSearch database.

Usage: %s [-h host[:port]] command [arg1 [arg2...]]

Commands:
export - Export crashes from a database.
    export_from_db [path=. [numberofdays=0]]
import - Import a dump file into an ElasticSearch instance.
    import dumpfile mappingfile
clear - Delete all socorro related indexes.
    clear
rebuild - Clear database and import a dump.
    rebuild dumpfile mappingfile

Options:
-h -- ElasticSearch host and port. Default is 'localhost:9200'.

"""

import csv
import datetime
import json
import os
import tarfile
import time
import sys

import config.commonconfig as configModule

import socorro.database.database as db
import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.datetimeutil as dtu
import socorro.lib.httpclient as httpc

config = configurationManager.newConfiguration(
    configurationModule=configModule,
    applicationName='movecrashes.py'
)


def export_uuids(path, numberofdays):
    """Export crash report uuids from a PostgreSQL database to a CSV file

    path - Directory where the csv file will be created.
    numberofdays - Number of days of crash reports to retrieve, before the most
                   recent crash date.

    """
    database = db.Database(config)
    connection = database.connection()
    cur = connection.cursor()

    # steps
    # 1. pull all distinct dates
    sql = """
        SELECT DISTINCT to_char(date_processed, 'YYYY-MM-DD') as day
        FROM reports
        ORDER BY day DESC
    """
    if numberofdays:
        sql = "%s LIMIT %s" % (sql, numberofdays)

    print 'Calculating dates... '
    days = db.execute(cur, sql)

    days_list = []
    for day in days:
        days_list.append(day[0])

    store_filename = 'uuids.csv'
    store_filename = os.path.normpath('%s/%s' % (path, store_filename))
    store_file = open(store_filename, 'w')
    store = csv.writer(store_file, delimiter=',', quotechar='"')
    print 'Store file created: %s' % store_filename

    for day in days_list:
        date_from = dtu.datetimeFromISOdateString(day)
        date_to = date_from + datetime.timedelta(1)

        sql = "SELECT uuid FROM reports WHERE date_processed BETWEEN %s AND %s"

        print 'Getting crash reports for day %s' % date_from.date()
        crashes_list = db.execute(cur, sql, (date_from, date_to))
        for crash in crashes_list:
            store.writerow(crash)

    store_file.close()
    connection.close()
    return store_filename


def export(path, numberofdays=0):
    """Export crash reports from a PostgreSQL database.

    path - Directory where the dump file will be created.
    numberofdays - Number of days of crash reports to retrieve, before the most
                   recent crash date.

    """
    database = db.Database(config)
    connection = database.connection()
    cur = connection.cursor()

    crash_files = []
    fields_list = ("client_crash_date",
                   "date_processed",
                   "uuid",
                   "product",
                   "version",
                   "build",
                   "signature",
                   "url",
                   "install_age",
                   "last_crash",
                   "uptime",
                   "cpu_name",
                   "cpu_info",
                   "reason",
                   "address",
                   "os_name",
                   "os_version",
                   "email",
                   "build_date",
                   "user_id",
                   "started_datetime",
                   "completed_datetime",
                   "success",
                   "truncated",
                   "processor_notes",
                   "user_comments",
                   "app_notes",
                   "distributor",
                   "distributor_version",
                   "topmost_filenames",
                   "addons_checked",
                   "flash_version",
                   "hangid",
                   "process_type",
                   "release_channel")

    # steps
    # 1. pull all distinct dates
    sql = """
        SELECT DISTINCT to_char(date_processed, 'YYYY-MM-DD') as day
        FROM reports
        ORDER BY day DESC
    """
    if numberofdays:
        sql = "%s LIMIT %s" % (sql, numberofdays)

    print 'Calculating dates... '
    days = db.execute(cur, sql)

    days_list = []
    for day in days:
        days_list.append(day[0])

    #~ days_list = [
        #~ '2012-03-04T00:00:00+00:00'
    #~ ]

    store_filename = 'dump.json'
    store_filename = os.path.normpath('%s/%s' % (path, store_filename))
    store = open(store_filename, 'w')
    print 'Store file created: %s' % store_filename

    indexes_filename = 'indexes.txt'
    indexes_filename = os.path.normpath('%s/%s' % (path, indexes_filename))
    indexes = open(indexes_filename, 'w')
    print 'Indexes file created: %s' % indexes_filename

    for day in days_list:
        date_from = dtu.datetimeFromISOdateString(day)
        date_to = date_from + datetime.timedelta(1)
        datestr = date_from.strftime('%y%m%d')
        es_index = 'socorro_%s' % datestr
        es_type = 'crash_reports'
        action_line = '{"index":{"_index":"%s","_type":"%s"}}\n' % (
                      es_index, es_type)

        indexes.write('%s\n' % es_index)

        # 2. for each date, pull all crashes of the day
        day_sql = " ".join(("SELECT %s" % ", ".join(fields_list),
                            "FROM reports",
                            "WHERE date_processed BETWEEN %s AND %s"))

        print 'Getting crash reports for day %s' % date_from.date()
        crashes_list = db.execute(cur, day_sql, (date_from, date_to))
        for crash in crashes_list:
            # 3. for each crash report
            json_crash = dict(zip(fields_list, crash))

            # stringify datetime fields
            for i in json_crash:
                if isinstance(json_crash[i], datetime.datetime):
                    json_crash[i] = dtu.date_to_string(json_crash[i])

            store.write(action_line)
            store.write('%s\n' % json.dumps(json_crash))

    store.close()
    crash_files.append(store_filename)
    indexes.close()
    crash_files.append(indexes_filename)
    connection.close()
    return generate_dump(crash_files, path)


def generate_dump(files, path):
    """Return the filename of a tar file containing all given files.
    """
    os.chdir(path)
    dumpfilename = './dump.tar'
    dumpfile = tarfile.open(dumpfilename, 'w')
    for name in files:
        dumpfile.add(name.replace(path, ''))
    dumpfile.close()

    return dumpfilename


def import_dump(es_connection, dump_filename, mapping_filename):
    """Import a dump into an ElasticSearch instance.

    filename - Path to the dump.
    es_connection - HTTP connection to ElasticSearch instance.

    """
    print 'Importing crashes from dump %s' % dump_filename

    dump = tarfile.open(dump_filename)
    path = '/tmp/'
    dump.extractall(path)
    members = dump.getnames()
    crash_file_handlers = []

    for crash_file in members:
        if 'indexes' in crash_file:
            indexes_file_handler = open('%s%s' % (path, crash_file), 'r')
        else:
            crash_file_handlers.append(open('%s%s' % (path, crash_file), 'r'))

    # PUT mapping for each index
    for es_index in indexes_file_handler:
        es_index = '/%s' % es_index.strip()
        es_uri = '%s/crash_reports' % es_index
        es_connection.put(es_index)
        import_mapping(es_connection, es_uri, mapping_filename)

    indexes_file_handler.close()

    sys.stdout.write('Indexing crash reports \r')
    sys.stdout.flush()
    for crash_file_handler in crash_file_handlers:
        i = 0
        j = 0
        maxLines = 50000
        stream = []
        for line in crash_file_handler:
            stream.append(line)
            i += 1
            if i >= maxLines:
                j += i
                sys.stdout.write('Indexing crash reports... %d \r' % j)
                sys.stdout.flush()
                es_connection.post('/_bulk?refresh=true', ''.join(stream))
                time.sleep(20)

                i = 0
                stream = []
        print '\rIndexing crash reports... %d' % (j + i)
        es_connection.post('/_bulk', ''.join(stream))
        crash_file_handler.close()
    print "Indexing done"


def delete_existing_indexes(es_connection):
    """Delete all socorro related indexes from an ElasticSearch instance.

    Concerned indexes are the ones matching '*socorro_*'.

    """
    print 'Clearing ElasticSearch instance... '

    http_response = es_connection.get("/_status")

    try:
        indexes = json.loads(http_response)
    except TypeError:
        print "An error occured while getting a list of all indexes from ES"
        print http_response

    for index in indexes["indices"]:
        if "socorro_" in index:
            http_response = es_connection.delete(index)


def import_mapping(es_connection, es_uri, mapping_filename):
    """
    """
    mapping = open(mapping_filename)
    uri = '%s/_mapping' % es_uri
    print 'Importing mapping from file %s to %s' % (mapping_filename, uri)
    es_connection.post(uri, mapping.read())
    mapping.close()


if __name__ == '__main__':
    # timing execution
    start_time = time.time()

    # default values
    day = datetime.date.today()
    numberofdays = 7
    crashes_per_day = 1000
    es_host = 'localhost'
    es_port = '9200'

    def usage():
        print __doc__ % sys.argv[0]

    if len(sys.argv) <= 1 or sys.argv[1] == '--help':
        usage()
        sys.exit(0)

    argi = 1
    if sys.argv[argi] == '-h':
        parts = sys.argv[argi + 1].split(':')
        es_host = parts[0]
        if len(parts) == 2:
            es_port = int(parts[1])
        argi += 2

    cmd = sys.argv[argi]
    args = sys.argv[argi + 1:]

    es_connection = httpc.HttpClient(es_host, es_port, timeout=60)

    if cmd == 'export':
        # default values
        path = '.'
        numberofdays = 0

        if len(args) >= 1:
            path = args[0]
        if len(args) >= 2:
            numberofdays = args[1]

        cfile = export(path, numberofdays)
        print 'Generated crash file: %s' % cfile

    if cmd == 'export_uuids':
        # default values
        path = '.'
        numberofdays = 0

        if len(args) >= 1:
            path = args[0]
        if len(args) >= 2:
            numberofdays = args[1]

        cfile = export_uuids(path, numberofdays)
        print 'Generated uuids file: %s' % cfile

    elif cmd == 'import':
        if len(args) != 2:
            usage()
            sys.exit(1)
        dump = args[0]
        mapping = args[1]
        with es_connection:
            import_dump(es_connection, dump, mapping)
        print 'Imported dump: %s' % dump

    elif cmd == 'clear':
        with es_connection:
            delete_existing_indexes(es_connection)
        print 'Database cleared'

    elif cmd == 'rebuild':
        if len(args) != 2:
            usage()
            sys.exit(1)
        dump = args[0]
        mapping = args[1]
        with es_connection:
            delete_existing_indexes(es_connection)
            import_dump(es_connection, dump, mapping)
        print 'Database cleared and rebuilt from dump: %s' % dump

    else:
        usage()
        sys.exit(0)

    # Nicely displaying the total time of execution
    exec_time = time.time() - start_time
    exec_hours = 0
    exec_minutes = 0
    exec_seconds = 0

    if exec_time > 3600:
        exec_hours = exec_time / 3600
        exec_time = exec_time % 3600
    if exec_time > 60:
        exec_minutes = exec_time / 60
        exec_time = exec_time % 60
    exec_seconds = exec_time

    print "Execution time: %d hours, %d minutes and %d seconds" % (
                                        exec_hours, exec_minutes, exec_seconds)
