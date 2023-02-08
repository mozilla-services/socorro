#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/recreate_s3_buckets.sh
#
# Deletes and recreates S3 bucket used for crash storage
#
# Note: This should be called from inside a container.

set -euo pipefail

cd /app

echo "Dropping and recreating S3 crash bucket..."
(./bin/socorro_aws_s3.sh rb "s3://${CRASHSTORAGE_S3_BUCKET}/" --force || true) 2> /dev/null # Ignore if it doesn't exist
./bin/socorro_aws_s3.sh mb "s3://${CRASHSTORAGE_S3_BUCKET}/"

echo "Dropping and recreating S3 telemetry bucket..."
(./bin/socorro_aws_s3.sh rb "s3://${TELEMETRY_S3_BUCKET}/" --force || true) 2> /dev/null # Ignore if it doesn't exist
./bin/socorro_aws_s3.sh mb "s3://${TELEMETRY_S3_BUCKET}/"
