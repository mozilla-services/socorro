#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Entrypoint for Socorro image

if [ -z "$*" ]; then
    echo "usage: socorro_entrypoint.sh SERVICE"
    exit 1
fi

SERVICE=$1
shift

case ${SERVICE} in
processor)
    /app/docker/run_processor.sh "$@"
    ;;
crontabber)
    /app/docker/run_crontabber.sh "$@"
    ;;
webapp)
    /app/docker/run_webapp.sh "$@"
    ;;
shell)
    if [ -z "$*" ]; then
        bash
    else
        "$@"
    fi
    ;;
*)
    echo "Unknown service ${SERVICE}"
    exit 1
esac
