#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs stage submitter in a local dev environment.

# NOTE(willkg): Don't use this in a server environment. If we ever get to the
# point where we want to run this in a server environment with this scaffolding,
# we should redo it.

set -e

# Run submitter sleeping 1 minute between runs
while true
do
    python socorro/submitter/submitter_app.py || true
    echo "Sleep 1 minutes..."
    sleep 60
done
