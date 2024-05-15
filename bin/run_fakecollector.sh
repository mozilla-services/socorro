#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_fakecollector.sh
#
# Runs a fake collector that parses submissions and outputs details to
# the log.
#
# Note: This is not a production-ready server. It's intended only for
# debugging.

set -euxo pipefail

PORT=8000

python fakecollector/collector.py --port=${PORT}
