#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)

echo 'add appid column to reports'
echo 'bug 706807'
psql -f ${CURDIR}/appid.sql breakpad

echo '2.3.5 upgrade done'

exit 0