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
DOCKER="$(which docker)"

# Use the same image we use for building docker images because it'll be cached
# already
BASEIMAGENAME="python:2.7.13-slim"

# Start services in background (this is idempotent)
echo "Starting services in the background..."
${DC} up -d elasticsearch
${DC} up -d postgresql
${DC} up -d rabbitmq

# Create a data container to hold the repo directory contents and copy the
# contents into it
if [ "$(docker container ls --all | grep socorro-repo)" == "" ]; then
    echo "Creating socorro-repo container..."
    docker create -v /app --name socorro-repo ${BASEIMAGENAME} /bin/true
fi
echo "Copying contents..."
docker cp . socorro-repo:/app

if [ "$1" == "--shell" ]; then
    echo "Running shell..."
    DOCKER_COMMAND="/bin/bash"
    DOCKER_ARGS="-t -i"
else
    echo "Running tests..."
    DOCKER_COMMAND="/app/docker/run_tests.sh"
    DOCKER_ARGS=""
fi

# Run cmd in that environment and then remove the container
docker run \
       --rm \
       --volumes-from socorro-repo \
       --workdir /app \
       --network socorro_default \
       --link socorro_elasticsearch_1 \
       --link socorro_postgresql_1 \
       --link socorro_rabbitmq_1 \
       --env-file ./docker/config/docker_common.env \
       --env-file ./docker/config/test.env \
       ${DOCKER_ARGS} local/socorro_webapp ${DOCKER_COMMAND}

echo "Done!"
