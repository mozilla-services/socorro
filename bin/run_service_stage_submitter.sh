#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_service_stage_submitter.sh
#
# Runs the stage submitter service.
#
# Note: This should be called from inside a container.

set -euo pipefail

export PROCESS_NAME=stage_submitter

# Run the stage_submitter
exec python socorro/stage_submitter/submitter.py
