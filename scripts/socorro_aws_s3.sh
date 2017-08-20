#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Wrapper for aws script that pulls connection bits from the environment.
#
# Usage:
#
# make bucket
#
#     scripts/socorro_aws_s3.sh mb s3://dev_bucket/
#
# list bucket
#
#     scripts/socorro_aws_s3.sh ls s3://dev_bucket/
#
# copy files into s3 container
#
#     scripts/socorro_aws_s3.sh cp --recursive ./my_s3_root/ s3://dev_bucket/
#
# sync local directory and s3 container
#
#     scripts/socorro_aws_s3.sh sync ./my_s3_root/ s3://dev_bucket/

# First convert configman environment vars which have bad identifiers to ones
# that don't
function getenv {
    python -c "import os; print os.environ['$1']"
}

AWS_HOST="$(getenv 'resource.boto.host')"
AWS_PORT="$(getenv 'resource.boto.port')"
AWS_ACCESS_KEY_ID="$(getenv 'resource.boto.access_key')"
AWS_SECRET_ACCESS_KEY="$(getenv 'secrets.boto.secret_access_key')"
AWS_BUCKET="$(getenv 'resource.boto.bucket_name')"

# Create required configuration files for aws
if [[ ! -d /tmp/.aws ]]
then
    mkdir /tmp/.aws
fi
if [[ ! -f /tmp/.aws/config ]]
then
    cat > /tmp/.aws/config <<EOF
[default]
EOF
fi
if [[ ! -f /tmp/.aws/credentials ]]
then
    cat > /tmp/.aws/credentials <<EOF
[default]
aws_access_key_id = ${AWS_ACCESS_KEY_ID}
aws_secret_access_key = ${AWS_SECRET_ACCESS_KEY}
EOF
fi

AWSOPTIONS="--endpoint-url=http://${AWS_HOST}:${AWS_PORT}/"

echo "S3 container bucket is ${AWS_BUCKET}"

HOME=/tmp /tmp/.local/bin/aws ${AWSOPTIONS} s3 $@
