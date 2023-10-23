#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/circleci-push.sh [LOCALIMAGE]
#
# Note: Don't use this--it's only used in CI.
#
# Environment variables used:
#
# DOCKER_USER/DOCKER_PASS: dockerhub credentials
# DOCKERHUB_REPO: name of the repo on dockerhub to use
# CIRCLE_BRANCH/CIRCLE_TAG: CircleCI generated environment variables

set -euo pipefail

function retry {
    set +e
    local n=0
    local max=3
    while true; do
    "$@" && break || {
        if [[ $n -lt $max ]]; then
            ((n++))
            echo "Command failed. Attempt $n/$max:"
        else
            echo "Failed after $n attempts."
            exit 1
        fi
    }
    done
    set -e
}

if [[ $# -eq 0 ]]; then
    echo "Usage: bin/circleci_push.sh [LOCALIMAGE]"
    exit 1
fi

LOCAL_IMAGE="$1"

if [ -z "${DOCKER_USER:-}" ] || [ -z "${DOCKER_PASS:-}" ] || [ -z "${DOCKERHUB_REPO:-}"]; then
    echo "Skipping Login to Dockerhub, credentials not available."
    exit
fi

echo "${DOCKER_PASS}" | docker login -u="${DOCKER_USER}" --password-stdin

if [ "${CIRCLE_BRANCH:-}" == "main" ]; then
    # deploy main latest
    REMOTE_IMAGE="${DOCKERHUB_REPO}:latest"
elif  [ -n "${CIRCLE_TAG:-}" ]; then
    # deploy a release tag
    REMOTE_IMAGE="${DOCKERHUB_REPO}:${CIRCLE_TAG}"
else
    echo "Build neither for the main branch nor for a tag, skipping Docker upload."
    exit
fi

echo "Pushing ${REMOTE_IMAGE}..."
docker tag "${LOCAL_IMAGE}" "${REMOTE_IMAGE}"
docker images
retry docker push "${REMOTE_IMAGE}"
