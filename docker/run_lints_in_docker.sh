#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Script that sets up the docker environment to run the lints in and runs the
# lints.

# Failures should cause setup to fail
set -v -e -x

DC="$(which docker-compose)"
APP_UID="10001"
APP_GID="10001"

# Use the same image we use for building docker images because it's cached.
# Otherwise this doesn't make any difference.
BASEIMAGENAME="python:2.7.14-slim"

# Figure out which image to run lints in
LINTIMAGE="local/socorro_webapp"

# Create a data container to hold the repo directory contents and copy the
# contents into it
if [ "$(docker container ls --all | grep socorro-repo)" == "" ]; then
echo "Creating socorro-repo container..."
docker create \
        -v /app \
        --user "${APP_UID}" \
        --name socorro-repo \
        "${BASEIMAGENAME}" /bin/true
fi
echo "Copying contents..."
# Wipe whatever might be in there from past runs
docker run \
        --user root \
        --volumes-from socorro-repo \
        --workdir /app \
        "${LINTIMAGE}" sh -c "rm -rf /app/*"

# Verify files are gone
docker run \
        --user root \
        --volumes-from socorro-repo \
        --workdir /app \
        "${LINTIMAGE}" ls -l /app/

# Copy the repo root into /app
docker cp . socorro-repo:/app

# Fix permissions in data container
docker run \
        --user root \
        --volumes-from socorro-repo \
        --workdir /app \
        "${LINTIMAGE}" chown -R "${APP_UID}:${APP_GID}" /app

# Run cmd in that environment and then remove the container
echo "Running lints..."
docker run \
        --rm \
        --user "${APP_UID}" \
        --volumes-from socorro-repo \
        --workdir /app/webapp-django \
        --tty \
        --interactive \
        "${LINTIMAGE}" /webapp-frontend-deps/node_modules/.bin/eslint .

echo "Done!"
