#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)

echo 'add productid column to reports'
echo 'bug 706807'
psql -f ${CURDIR}/productid.sql breakpad

echo '2.3.5 upgrade done'

exit 0