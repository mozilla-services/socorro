#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


#please see README

set -e

CURDIR=$(dirname $0)

echo 'create table if not exists function'
psql -f ${CURDIR}/create_table_if_not_exists.sql breakpad

echo 'alter the releases_raw table so that it can accept nightlies'
psql -f ${CURDIR}/alter_releases_raw.sql breakpad

echo 'new support functions, mostly timestamp conversion'
psql -f ${CURDIR}/support_functions.sql breakpad

exit 0
