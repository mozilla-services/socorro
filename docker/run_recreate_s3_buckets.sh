#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Deletes and recreates S3 bucket used for crash storage

cd /app

echo "Dropping and recreating S3 bucket..."
(./scripts/socorro_aws_s3.sh rb s3://dev_bucket/ --force || true) 2> /dev/null # Ignore if it doesn't exist
./scripts/socorro_aws_s3.sh mb s3://dev_bucket/
