#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Wrapper for aws script that pulls connection bits from the environment.
#
# Usage:
#
# make bucket
#
#     bin/socorro_aws_s3.sh mb s3://dev-bucket/
#
# list bucket
#
#     bin/socorro_aws_s3.sh ls s3://dev-bucket/
#
# copy files into s3 container
#
#     bin/socorro_aws_s3.sh cp --recursive ./my_s3_root/ s3://dev-bucket/
#
# sync local directory and s3 container
#
#     bin/socorro_aws_s3.sh sync ./my_s3_root/ s3://dev-bucket/
#
# Note: This should be called from inside a container.

set -euo pipefail

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
aws_access_key_id = ${CRASHSTORAGE_S3_ACCESS_KEY}
aws_secret_access_key = ${CRASHSTORAGE_S3_SECRET_ACCESS_KEY}
EOF
fi

AWSOPTIONS="--endpoint-url=${AWS_ENDPOINT_URL}"

HOME=/tmp aws ${AWSOPTIONS} s3 $@
