#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.4.3

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'fix idempotency issue with updating socorro version'
echo 'no bug'
psql -f ${CURDIR}/update_socorro_version.sql breakpad

echo '*********************************************************'
echo 'fix sorting for 3-digit betas'
echo 'bug 721456'
psql -f ${CURDIR}/new_version_sort.sql breakpad
psql -f ${CURDIR}/backfill_version_sorts.sql breakpad

echo '*********************************************************'
echo 'add user and permissions for new analyst user'
echo 'bug 687906'
psql -f ${CURDIR}/create_user_analyst.sql breakpad

echo '*********************************************************'
echo 'drop frames table'
echo 'bug 681476'
psql -f ${CURDIR}/drop_frames_table.sql breakpad

echo '*********************************************************'
echo 'Fix FKs so that we can delete product/versions'
echo 'No bug #'
psql -f ${CURDIR}/fix_product_version_fks.sql breakpad

echo '*********************************************************'
echo 'NOTICE: for the new analyst user you must do two additional,'
echo 'manual upgrade steps if they have not been done already:'
echo '1. create analyst user in pgbouncer-processor.ini'
echo '2. create database password for analyst user.'
echo '*********************************************************'

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0