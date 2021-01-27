#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_crontabber.sh
#
# Runs cronrun (used to be called crontabber).
#
# Note: This should be called from inside a container.

set -euo pipefail

# Number of seconds to let cronrun run before determining it's hung.
KILL_TIMEOUT=3600

# Run cronrun sleeping 5 minutes between runs
while true
do
    # NOTE(willkg): cronrun can probably hang, so we wrap it in a timeout.
    # Also, we don't want cronrun to die and then have that kill the container,
    # so we do the || true thing.
    timeout --signal KILL "${KILL_TIMEOUT}" ./webapp-django/manage.py cronrun || true
    echo "Sleep 5 minutes..."
    sleep 300
done
