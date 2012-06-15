#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)

echo 'fix hang_report matview and backfill hang_reports'
echo 'bug 710465'
psql -f ${CURDIR}/hang_report.sql breakpad
psql -f ${CURDIR}/backfill_hang_report.sql breakpad

echo '2.3.4.1 upgrade done'

exit 0