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
# DOCKER_REPO: name of the repo on dockerhub to use
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
DOCKER_USER="${DOCKER_USER:-}"
DOCKER_PASS="${DOCKER_PASS:-}"

if [ "${DOCKER_USER}" == "" ] || [ "${DOCKER_PASS}" == "" ]; then
    echo "Skipping Login to Dockerhub, credentials not available."
    exit
fi


echo "${DOCKER_PASS}" | docker login -u="${DOCKER_USER}" --password-stdin

if [ "${CIRCLE_BRANCH}" == "main" ]; then
    # deploy main latest
    docker tag "${LOCAL_IMAGE}" "${DOCKERHUB_REPO}:latest"
    retry docker push "${DOCKERHUB_REPO}:latest"
elif  [ ! -z "${CIRCLE_TAG}" ]; then
    # deploy a release tag
    echo "${DOCKERHUB_REPO}:${CIRCLE_TAG}"
    docker tag "${LOCAL_IMAGE}" "${DOCKERHUB_REPO}:${CIRCLE_TAG}"
    docker images
    retry docker push "${DOCKERHUB_REPO}:${CIRCLE_TAG}"
fi
