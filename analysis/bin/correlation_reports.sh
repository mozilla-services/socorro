#! /bin/sh
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


if [ "$#" -ne 3 ]
then
    echo "Usage: $0 <product> <release> <yyyyMMdd>"
    exit 1
fi

PRODUCT=$1
RELEASE=$2
DATE=$3
PYTHON="/usr/bin/python26"
HADOOP="/usr/lib/hadoop/bin/hadoop"
REPORTS_HOME="/usr/local/socorro/correlation-reports"

${HADOOP} jar ${REPORTS_HOME}/crash-reports-job.jar com.mozilla.socorro.hadoop.PerCrashCoreCount -Dproduct.filter=${PRODUCT} -Drelease.filter=${RELEASE} -Dstart.date=${DATE} -Dend.date=${DATE} ${DATE}-${PRODUCT}-${RELEASE}-core-counts
${HADOOP} fs -getmerge ${DATE}-${PRODUCT}-${RELEASE}-core-counts /tmp/${DATE}-${PRODUCT}-${RELEASE}-core-counts.data
${PYTHON} ${REPORTS_HOME}/per-crash-core-count-hadoop.py /tmp/${DATE}-${PRODUCT}-${RELEASE}-core-counts.data > /tmp/${DATE}_${PRODUCT}_${RELEASE}-core-counts.txt
${HADOOP} jar ${REPORTS_HOME}/crash-reports-job.jar com.mozilla.socorro.hadoop.PerCrashInterestingModules -Dproduct.filter=${PRODUCT} -Drelease.filter=${RELEASE} -Dstart.date=${DATE} -Dend.date=${DATE} ${DATE}-${PRODUCT}-${RELEASE}-interesting-modules
${HADOOP} fs -getmerge ${DATE}-${PRODUCT}-${RELEASE}-interesting-modules /tmp/${DATE}-${PRODUCT}-${RELEASE}-interesting-modules.data
${PYTHON} ${REPORTS_HOME}/per-crash-interesting-modules-hadoop.py /tmp/${DATE}-${PRODUCT}-${RELEASE}-interesting-modules.data > /tmp/${DATE}_${PRODUCT}_${RELEASE}-interesting-modules.txt
${PYTHON} ${REPORTS_HOME}/per-crash-interesting-modules-hadoop.py -v /tmp/${DATE}-${PRODUCT}-${RELEASE}-interesting-modules.data > /tmp/${DATE}_${PRODUCT}_${RELEASE}-interesting-modules-with-versions.txt
${HADOOP} jar ${REPORTS_HOME}/crash-reports-job.jar com.mozilla.socorro.hadoop.PerCrashInterestingModules -Dproduct.filter=${PRODUCT} -Drelease.filter=${RELEASE} -Dstart.date=${DATE} -Dend.date=${DATE} -Daddons=true ${DATE}-${PRODUCT}-${RELEASE}-interesting-addons
${HADOOP} fs -getmerge ${DATE}-${PRODUCT}-${RELEASE}-interesting-addons /tmp/${DATE}-${PRODUCT}-${RELEASE}-interesting-addons.data
${PYTHON} ${REPORTS_HOME}/per-crash-interesting-modules-hadoop.py -a /tmp/${DATE}-${PRODUCT}-${RELEASE}-interesting-addons.data > /tmp/${DATE}_${PRODUCT}_${RELEASE}-interesting-addons.txt
${PYTHON} ${REPORTS_HOME}/per-crash-interesting-modules-hadoop.py -a -v /tmp/${DATE}-${PRODUCT}-${RELEASE}-interesting-addons.data > /tmp/${DATE}_${PRODUCT}_${RELEASE}-interesting-addons-with-versions.txt

rm /tmp/*.data
find /tmp -name ${DATE}\* -type f -size +500k | xargs gzip -9
