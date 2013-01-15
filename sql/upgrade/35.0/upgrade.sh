#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=35.0

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql $DBNAME

echo '*********************************************************'
echo 'add MetroFirefox to database'
echo 'bug 791218'
psql -f ${CURDIR}/add_metrofirefox.sql $DBNAME
psql -f ${CURDIR}/update_product_versions.sql $DBNAME

echo '*********************************************************'
echo 'add rapid_beta_version to add_new_products()'
echo 'bug 823296'
psql -f ${CURDIR}/add_new_product.sql $DBNAME

echo '*********************************************************'
echo 'Add emails table'
echo 'bug 814647'
psql -f ${CURDIR}/emails.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0
