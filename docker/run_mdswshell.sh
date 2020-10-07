#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Sets up a shell in a container for building and debugging minidump-stackwalk.

set -e

INDOCKER=${INDOCKER:-0}

if [[ ${INDOCKER} -eq 1 ]]; then
    # Save the virtualenv in /app because that's mounted locally and saves some
    # time between invocations
    python -m venv /app/mdsw_venv/
    source /app/mdsw_venv/bin/activate
    pip install -r requirements/default.txt -c requirements/constraints.txt

    # Build symbols directories so minidump-stackwalk can use them
    mkdir -p /tmp/symbols/cache
    mkdir -p /tmp/symbols/tmp

    # Output some helpful stuff
    echo "====================================================================="
    echo "See https://socorro.readthedocs.io/en/latest/stackwalk.html for docs."
    echo "====================================================================="

    # Drop into the shell
    /bin/bash
    exit;
fi

DOCKER="$(which docker)"
SOCORRO_UID=${SOCORRO_UID:-"10001"}
TAG="local/socorro-breakpad:latest"

# Build the image stopping at the minidump-stackwalk stage
${DOCKER} build \
          --build-arg userid=${SOCORRO_UID} \
          --build-arg groupid=${SOCORRO_GID} \
          --file ./docker/Dockerfile \
          --target socorro_breakpad \
          --tag "${TAG}" \
          .

# Run the image in a container
${DOCKER} run \
          --user=${SOCORRO_UID} \
          --volume="$(pwd)":/app \
          --workdir=/app \
          --env-file=./docker/config/local_dev.env \
          --env-file=./my.env \
          --env=INDOCKER=1 \
          --tty \
          --interactive \
          ${TAG} \
          /app/docker/run_mdswshell.sh
