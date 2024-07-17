#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/setup_services.sh
#
# Deletes all service state data and rebuilds database tables, buckets,
# and other service state.
#
# Note: This should be called from inside a container.

set -euo pipefail

# Drop and re-create the breakpad database with tables, stored procedures,
# types, indexes, and keys; also bulk-loads static data for some lookup tables
/app/bin/setup_postgres.sh

# Delete and create local GCS buckets
/app/socorro-cmd gcs delete "${CRASHSTORAGE_GCS_BUCKET}"
/app/socorro-cmd gcs create "${CRASHSTORAGE_GCS_BUCKET}"
/app/socorro-cmd gcs delete "${TELEMETRY_GCS_BUCKET}"
/app/socorro-cmd gcs create "${TELEMETRY_GCS_BUCKET}"

# Delete and create Elasticsearch indices
/app/socorro-cmd es delete
/app/socorro-cmd es create

# Delete and create Pub/Sub queues
/app/socorro-cmd pubsub delete-all
/app/socorro-cmd pubsub create-all

# Initialize the cronrun bookkeeping for all configured jobs to success
/app/webapp/manage.py cronmarksuccess all
