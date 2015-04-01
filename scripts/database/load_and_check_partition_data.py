#!/usr/bin/env python

import datetime
import glob
import os
import os.path
import subprocess

if len(sys.argv) != 2:
    print "USAGE: %s [parent table]"
    exit

parent_table = sys.argv[1]
partition_dir = os.path.join("partitions", parent_table)

# Iterate through all split up dump files
for filename in glob.glob(os.path.join(partition_dir, "*")):
    print "INFO: processing", filename
    (partition, suffix) = os.path.basename(filename).split('.')

    # construct date range
    start = datetime.datetime.strptime(partition, '%Y%m%d').date()
    end = start + datetime.timedelta(6)

    # SQL for checking rowcounts pre-partition and post-partition
    before_sql = "SELECT count(*) from %s WHERE report_date BETWEEN '%s' AND '%s'" % (
        parent_table, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
    )
    after_sql = """ SELECT count(*) from %s """ % (parent_table + '_' + partition)

    before_count = 0
    before_count = os.popen('psql breakpad -AX -qt -c "%s"' % before_sql).read().rstrip()

    if before_count > 0:
        # Load data into a partition
        os.system("psql breakpad -f %s" % filename)
        after_count = os.popen('psql breakpad -AX -qt -c "%s"' % after_sql).read().rstrip()

        print "INFO: before:", before_count, "after:", after_count
        if int(before_count) != int(after_count):
            print "ERROR: counts did not match for file", filename
    else:
        print "ERROR: before count is %i" % before_count
