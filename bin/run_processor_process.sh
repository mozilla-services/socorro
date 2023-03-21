#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_processor_process.sh
#
# Runs the processor process.
#
# Note: This should be called from inside a container.

set -euo pipefail

export PROCESS_NAME=processor

# Run the processor
python socorro/processor/processor_app.py
