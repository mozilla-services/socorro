#! /bin/sh

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

# build the list, sort it, and then upload the result
${HADOOP} jar $HOME_DIRECTORY/socorro-analysis-job.jar com.mozilla.socorro.hadoop.CrashReportModuleList -Dproduct.filter="${PRODUCT}" -Dos.filter="${OS}" -Dstart.date=${DATE} -Dend.date=${DATE} ${DATE}-modulelist-out
${HADOOP} fs -getmerge ${DATE}-modulelist-out /tmp/${DATE}-modulelist.txt
/bin/sort /tmp/${DATE}-modulelist.txt -o /tmp/${DATE}-modulelist.sorted.txt
scp /tmp/${DATE}-modulelist.sorted.txt people.mozilla.org:./public_html/${DATE}-modulelist.txt

# cleanup
${HADOOP} fs -rmr ${DATE}-modulelist-out
rm /tmp/${DATE}-modulelist.txt
rm /tmp/${DATE}-modulelist.sorted.txt