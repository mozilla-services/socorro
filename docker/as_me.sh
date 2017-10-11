#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Helper wrapper to run a script in the processor container "as me" so that
# files that it generates are owned by me.
#
# Usage:
#
#     ./docker/as_me.sh scripts/fetch_crash_data.py . crashid
#
# Takes a --container CONTAINER argument for specifying a container other than
# processor.

set -e

HOSTUSER=$(id -u):$(id -g)

if [[ $1 == "--container" ]]; then
    shift;
    CONTAINER=$1
    shift;
else
    CONTAINER=processor
fi

docker-compose run -u "${HOSTUSER}" ${CONTAINER} $@
