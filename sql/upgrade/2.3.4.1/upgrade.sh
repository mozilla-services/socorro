#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)

echo 'fix hang_report matview and backfill hang_reports'
echo 'bug 710465'
psql -f ${CURDIR}/hang_report.sql breakpad
psql -f ${CURDIR}/backfill_hang_report.sql breakpad

echo '2.3.4.1 upgrade done'

exit 0