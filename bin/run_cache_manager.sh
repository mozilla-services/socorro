#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_cache_manager.sh
#
# Runs the processor cache manager.
#
# Note: This should be called from inside a container.

set -euo pipefail

export PROCESS_NAME=cache_manager

# Run the processor
exec python socorro/processor/cache_manager.py
