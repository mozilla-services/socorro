#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.5.2

echo '*********************************************************'
echo 'create function for adding old versions to productdims'
echo 'in order to support Camino'
echo 'bug 731738'
psql -f ${CURDIR}/add_old_release.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0