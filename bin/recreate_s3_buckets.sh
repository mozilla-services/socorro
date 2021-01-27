#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Deletes and recreates S3 bucket used for crash storage

# First convert configman environment vars which have bad identifiers to ones
# that don't
function getenv {
    python -c "import os; print(os.environ['$1'])"
}

BUCKET="$(getenv 'resource.boto.bucket_name')"
TELEMETRY_BUCKET="$(getenv 'destination.telemetry.bucket_name')"


cd /app

echo "Dropping and recreating S3 crash bucket..."
(./scripts/socorro_aws_s3.sh rb "s3://${BUCKET}/" --force || true) 2> /dev/null # Ignore if it doesn't exist
./scripts/socorro_aws_s3.sh mb "s3://${BUCKET}/"

echo "Dropping and recreating S3 telemetry bucket..."
(./scripts/socorro_aws_s3.sh rb "s3://${TELEMETRY_BUCKET}/" --force || true) 2> /dev/null # Ignore if it doesn't exist
./scripts/socorro_aws_s3.sh mb "s3://${TELEMETRY_BUCKET}/"
