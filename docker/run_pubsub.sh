#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs Pub/Sub emulator inside the pubsub container

# Set up project and run Pub/Sub
mkdir -p /tmp/data
gcloud config set project "${PUBSUB_PROJECT_ID}"
gcloud beta emulators pubsub start \
    --data-dir=/tmp/data \
    --host-port=0.0.0.0:${PUBSUB_PORT}
