#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Convenience wrapper for running socorro_aws.sh script in a container with a
# uid/gid that will respect file permissions.

HOSTUSER=$(id -u):$(id -g)

docker-compose run -u ${HOSTUSER} processor /app/scripts/socorro_aws_s3.sh $@
