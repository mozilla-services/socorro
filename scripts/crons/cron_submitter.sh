# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Pull raw, unprocessed crashes from an existing Socorro install
# and re-submit to an existing (dev, staging) instance elsewhere.

# Import settings
. /etc/socorro/socorrorc
export PGPASSWORD=$databasePassword

# Override Hbase settings on admin box
. /etc/socorro/socorro-monitor.conf

$PYTHON /data/socorro/application/socorro/collector/submitter_app.py --admin.conf=/etc/socorro/cron_submitter.ini