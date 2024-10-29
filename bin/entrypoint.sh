#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/entrypoint.sh SERVICE
#
# Entrypoint script for the Docker image.
#
# Note: This should be called from inside a container.

set -euo pipefail

# Entrypoint for Socorro image

if [ -z "$*" ]; then
    echo "usage: entrypoint.sh SERVICE"
    echo ""
    echo "Services:"
    grep -E '^[a-zA-Z0-9_-]+).*?## .*$$' bin/entrypoint.sh \
        | grep -v grep \
        | sed -n 's/^\(.*\)) \(.*\)##\(.*\)/* \1:\3/p'
    exit 1
fi

SERVICE=$1
shift

case ${SERVICE} in
processor)  ## Run processor service
    exec /app/bin/run_service_processor.sh "$@"
    ;;
crontabber)  ## Run crontabber service
    exec /app/bin/run_service_crontabber.sh "$@"
    ;;
webapp)  ## Run webapp service
    exec /app/bin/run_service_webapp.sh "$@"
    ;;
stage_submitter)  ## Runs the stage submitter
    exec /app/bin/run_service_stage_submitter.sh
    ;;
fakecollector)  ## Runs a local fake collector
    exec /app/bin/run_fakecollector.sh
    ;;
symbolsserver)  ## Runs a local symbols server
    exec /app/bin/run_symbolsserver.sh
    ;;
shell)  ## Open a shell or run something else
    if [ -z "$*" ]; then
        exec bash
    else
        exec "$@"
    fi
    ;;
*)
    echo "Unknown service ${SERVICE}"
    exit 1
esac
