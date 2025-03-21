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

# wait for dev services to start up
./bin/waitfor_services.sh

# Drop and re-create the breakpad database with tables, stored procedures,
# types, indexes, and keys; also bulk-loads static data for some lookup tables
/app/bin/setup_postgres.sh

# Delete and create local GCS buckets
gcs-cli delete "${CRASHSTORAGE_GCS_BUCKET}"
gcs-cli create "${CRASHSTORAGE_GCS_BUCKET}"
gcs-cli delete "${TELEMETRY_GCS_BUCKET}"
gcs-cli create "${TELEMETRY_GCS_BUCKET}"

# Delete and create Elasticsearch indices
/app/socorro-cmd es delete
/app/socorro-cmd es create

# Delete and create Pub/Sub queues
pubsub-cli delete-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_STANDARD_TOPIC_NAME"
pubsub-cli delete-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_PRIORITY_TOPIC_NAME"
pubsub-cli delete-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_REPROCESSING_TOPIC_NAME"

pubsub-cli create-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_STANDARD_TOPIC_NAME"
pubsub-cli create-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_PRIORITY_TOPIC_NAME"
pubsub-cli create-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_REPROCESSING_TOPIC_NAME"
pubsub-cli create-subscription "$PUBSUB_PROJECT_ID" "$PUBSUB_STANDARD_TOPIC_NAME" "$PUBSUB_STANDARD_SUBSCRIPTION_NAME"
pubsub-cli create-subscription "$PUBSUB_PROJECT_ID" "$PUBSUB_PRIORITY_TOPIC_NAME" "$PUBSUB_PRIORITY_SUBSCRIPTION_NAME"
pubsub-cli create-subscription "$PUBSUB_PROJECT_ID" "$PUBSUB_REPROCESSING_TOPIC_NAME" "$PUBSUB_REPROCESSING_SUBSCRIPTION_NAME"

# Initialize the cronrun bookkeeping for all configured jobs to success
/app/webapp/manage.py cronmarksuccess all
