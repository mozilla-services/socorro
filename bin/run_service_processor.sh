#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_service_processor.sh
#
# Runs processor service. The processor service is composed of two processes:
#
# * processor
# * cache_manager
#
# Note: This should be called from inside a container.

set -euo pipefail

PROCESSOR_WORKERS=${PROCESSOR_WORKERS:-"1"}

# Run honcho with PROCESSOR_WORKERS number of processor worker processes
honcho \
    --procfile /app/processor/Procfile \
    --app-root /app \
    --no-prefix \
    start \
    --concurrency "processor=${PROCESSOR_WORKERS}"
