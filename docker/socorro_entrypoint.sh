#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Entrypoint for Socorro image

if [ -z "$*" ]; then
    echo "usage: socorro_entrypoint.sh SERVICE"
    echo ""
    echo "Services:"
    grep -E '^[a-zA-Z0-9_-]+).*?## .*$$' docker/socorro_entrypoint.sh \
        | grep -v grep \
        | sed -n 's/^\(.*\)) \(.*\)##\(.*\)/* \1:\3/p'
    exit 1
fi

SERVICE=$1
shift

case ${SERVICE} in
processor)  ## Run processor service
    /app/docker/run_processor.sh "$@"
    ;;
crontabber)  ## Run crontabber service
    /app/docker/run_crontabber.sh "$@"
    ;;
webapp)  ## Run webapp service
    /app/docker/run_webapp.sh "$@"
    ;;
shell)  ## Open a shell or run something else
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
