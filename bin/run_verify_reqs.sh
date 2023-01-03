#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_verify_reqs.sh
#
# Verifies that the requirements file is built by the version of Python that
# runs in the container.

set -euo pipefail

cp requirements.txt requirements.txt.orig
pip-compile --quiet --generate-hashes --strip-extras
diff requirements.txt requirements.txt.orig
