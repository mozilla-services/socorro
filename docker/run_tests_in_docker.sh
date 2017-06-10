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
APP_UID="10001"
APP_GID="10001"

# Use the same image we use for building docker images because it'll be cached
# already
BASEIMAGENAME="python:2.7.13-slim"

# Start services in background (this is idempotent)
echo "Starting services in the background..."
${DC} up -d elasticsearch
${DC} up -d postgresql
${DC} up -d rabbitmq

# If we're running a shell, then we start up a test container with . mounted
# to /app.
if [ "$1" == "--shell" ]; then
    echo "Running shell..."

    docker run \
           --rm \
           --user "${APP_UID}" \
           --volume "$(pwd)":/app \
           --workdir /app \
           --network socorro_default \
           --link socorro_elasticsearch_1 \
           --link socorro_postgresql_1 \
           --link socorro_rabbitmq_1 \
           --env-file ./docker/config/docker_common.env \
           --env-file ./docker/config/test.env \
           --tty \
           --interactive \
           local/socorro_webapp /bin/bash

else
    # Create a data container to hold the repo directory contents and copy the
    # contents into it
    if [ "$(docker container ls --all | grep socorro-repo)" == "" ]; then
        echo "Creating socorro-repo container..."
        docker create \
               -v /app \
               --user "${APP_UID}" \
               --name socorro-repo \
               ${BASEIMAGENAME} /bin/true
    fi
    echo "Copying contents..."
    # Wipe whatever might be in there from past runs
    docker run \
           --user root \
           --volumes-from socorro-repo \
           --workdir /app \
           local/socorro_webapp sh -c "rm -rf /app/*"

    # Verify files are gone
    docker run \
           --user root \
           --volumes-from socorro-repo \
           --workdir /app \
           local/socorro_webapp ls -l /app/

    # Copy the repo root into /app
    docker cp . socorro-repo:/app

    # Fix permissions in data container
    docker run \
           --user root \
           --volumes-from socorro-repo \
           --workdir /app \
           local/socorro_webapp chown -R "${APP_UID}:${APP_GID}" /app

    # Run cmd in that environment and then remove the container
    echo "Running tests..."
    docker run \
           --rm \
           --user "${APP_UID}" \
           --volumes-from socorro-repo \
           --workdir /app \
           --network socorro_default \
           --link socorro_elasticsearch_1 \
           --link socorro_postgresql_1 \
           --link socorro_rabbitmq_1 \
           --env-file ./docker/config/docker_common.env \
           --env-file ./docker/config/test.env \
           local/socorro_webapp /app/docker/run_tests.sh

    echo "Done!"
fi
