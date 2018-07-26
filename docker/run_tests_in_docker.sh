#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Script that sets up the docker environment to run the tests in and runs the
# tests.

# Pass --shell to run a shell in the test container.

# Failures should cause setup to fail
set -v -e -x

# Set PS4 so it's easier to differentiate between this script and run_tests.sh
# running
PS4="+ (run_tests_in_docker.sh): "

DC="$(which docker-compose)"
SOCORRO_UID=${SOCORRO_UID:-"10001"}
SOCORRO_GID=${SOCORRO_GID:-"10001"}

# Use the same image we use for building docker images because it's cached.
# Otherwise this doesn't make any difference.
BASEIMAGENAME="python:2.7.14-slim"

# Figure out which image to run tests in
USEPYTHON="${USEPYTHON:-2}"
echo "${USEPYTHON}"
if [ "${USEPYTHON}" == "2" ]; then
    echo "Using Python 2.7.14."
    TESTIMAGE="local/socorro_webapp"
else
    echo "Using Python 3.6.5."
    TESTIMAGE="local/socorro_python3"
fi

# Start services in background (this is idempotent)
echo "Starting services needed by tests in the background..."
${DC} up -d elasticsearch
${DC} up -d postgresql
${DC} up -d rabbitmq
${DC} up -d statsd

# If we're running a shell, then we start up a test container with . mounted
# to /app.
if [ "$1" == "--shell" ]; then
    echo "Running shell..."

    docker run \
           --rm \
           --user "${SOCORRO_UID}" \
           --volume "$(pwd)":/app \
           --workdir /app \
           --network socorro_default \
           --link socorro_elasticsearch_1 \
           --link socorro_postgresql_1 \
           --link socorro_rabbitmq_1 \
           --link socorro_statsd_1 \
           --env-file ./docker/config/local_dev.env \
           --env-file ./docker/config/never_on_a_server.env \
           --env-file ./docker/config/test.env \
           --tty \
           --interactive \
           "${TESTIMAGE}" /bin/bash

else
    # Create a data container to hold the repo directory contents and copy the
    # contents into it
    if [ "$(docker container ls --all | grep socorro-repo)" == "" ]; then
        echo "Creating socorro-repo container..."
        docker create \
               -v /app \
               --user "${SOCORRO_UID}" \
               --name socorro-repo \
               "${BASEIMAGENAME}" /bin/true
    fi
    echo "Copying contents..."
    # Wipe whatever might be in there from past runs
    docker run \
           --user root \
           --volumes-from socorro-repo \
           --workdir /app \
           "${TESTIMAGE}" sh -c "rm -rf /app/*"

    # Verify files are gone
    docker run \
           --user root \
           --volumes-from socorro-repo \
           --workdir /app \
           "${TESTIMAGE}" ls -l /app/

    # Copy the repo root into /app
    docker cp . socorro-repo:/app

    # Fix permissions in data container
    docker run \
           --user root \
           --volumes-from socorro-repo \
           --workdir /app \
           "${TESTIMAGE}" chown -R "${SOCORRO_UID}:${SOCORRO_GID}" /app

    # Run cmd in that environment and then remove the container
    echo "Running tests..."
    docker run \
           --rm \
           --user "${SOCORRO_UID}" \
           --volumes-from socorro-repo \
           --workdir /app \
           --network socorro_default \
           --link socorro_elasticsearch_1 \
           --link socorro_postgresql_1 \
           --link socorro_rabbitmq_1 \
           --link socorro_statsd_1 \
           --env-file ./docker/config/local_dev.env \
           --env-file ./docker/config/never_on_a_server.env \
           --env-file ./docker/config/test.env \
           -e USEPYTHON="${USEPYTHON}" \
           --tty \
           --interactive \
           "${TESTIMAGE}" /app/docker/run_tests.sh

    echo "Done!"
fi
