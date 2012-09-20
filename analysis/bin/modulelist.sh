#! /bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


if [ "$#" -ne 3 ]
then
    echo "Usage: $0 <product> <os> <yyyyMMdd>"
    exit 1
fi

PRODUCT=$1
OS=$2
DATE=$3
HOME_DIRECTORY=$( cd "$( dirname "$0" )" && pwd )
HADOOP="/usr/lib/hadoop/bin/hadoop"

function fatal {
  if [ "$#" != "2" ]
  then
    echo "syntax: fatal <exit_code> <message>"
    return 1
  fi

  exit_code=$1
  message=$2

  if [ "$exit_code" != 0 ]
  then
    echo "Fatal exit code: $exit_code"
    echo $message
    exit $exit_code
  fi
}


# build the list, sort it, and then upload the result
${HADOOP} jar $HOME_DIRECTORY/socorro-analysis-job.jar com.mozilla.socorro.hadoop.CrashReportModuleList -Dproduct.filter="${PRODUCT}" -Dos.filter="${OS}" -Dstart.date=${DATE} -Dend.date=${DATE} ${DATE}-modulelist-out
fatal $? "Hadoop run failed"
${HADOOP} fs -getmerge ${DATE}-modulelist-out /tmp/${DATE}-modulelist.txt
fatal $? "fs getmerge failed"
/bin/sort /tmp/${DATE}-modulelist.txt -o /tmp/${DATE}-modulelist.sorted.txt
fatal $? "sort failed"

mkdir -p /mnt/crashanalysis/crash_analysis/modulelist
fatal $? "could not create output dir"
cp /tmp/${DATE}-modulelist.sorted.txt /mnt/crashanalysis/crash_analysis/modulelist/${DATE}-modulelist.txt
fatal $? "could not copy output file to output dir"

# cleanup
${HADOOP} fs -rmr ${DATE}-modulelist-out
fatal $? "could not remove modulelist from hdfs"
rm /tmp/${DATE}-modulelist.txt
fatal $? "could not remove unsorted modulelist"
rm /tmp/${DATE}-modulelist.sorted.txt
fatal $? "could not remove sorted modulelist"
