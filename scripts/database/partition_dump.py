#!/usr/bin/env python

import datetime
import os.path
import os, errno
import re
import sys


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def dsToWeeklyPartition(ds):
    d = datetime.datetime.strptime(ds, '%Y-%m-%d').date()
    last_monday = d + datetime.timedelta(0 - d.weekday())
    return last_monday.strftime('%Y%m%d')

if len(sys.argv) != 2:
    print "usage: %s [psql dump filename]" % sys.argv[0]
    exit

filename = sys.argv[1]
(tablename, suffix) = filename.split('.')

partition_dir = os.path.join("partitions", tablename)
mkdir_p(partition_dir)

open_files = {}
with open(filename, "r") as sql:
    for line in sql:
        # if line starts with COPY, save it for later
        if re.match('^COPY ', line):
            copy_line = line
            continue
        try:
            stuff = line.split("\t")
            ds = datetime.datetime.strptime(stuff[0], '%Y-%m-%d').date()
            partition = dsToWeeklyPartition(stuff[0])
        except:
            # Skip non-data lines
            continue

        if open_files.get(partition):
            open_files[partition].write(line)
        else:
            print "INFO: creating file for weekly partition:", partition
            part_path = os.path.join(partition_dir, partition + '.sql')
            myfile = open(part_path, "a")
            # replace table name with partition name
            copy_partition_line = re.sub(r"^COPY (\w+) ", r"COPY \1_%s" % partition, copy_line)
            myfile.write(copy_partition_line)
            myfile.write(line)
            open_files[partition] = myfile


for partition in open_files.keys():
    open_files[partition].write("\\.\n")
    open_files[partition].close()
