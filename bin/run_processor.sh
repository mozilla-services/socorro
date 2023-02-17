#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_processor.sh
#
# Runs processor process manager.
#
# Note: This should be called from inside a container.

set -euo pipefail

PROCESSOR_WORKERS=${PROCESSOR_WORKERS:-"1"}

# Run honcho with PROCESSOR_WORKERS number of processor worker processes
honcho \
    --procfile /app/processor/Procfile \
    --app-root /app \
    start \
    --concurrency "processor=${PROCESSOR_WORKERS}"
