#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/lint.sh [--fix]
#
# Runs linting and code fixing.
#
# Note: This should be called from inside a container.

set -euo pipefail

FILES="socorro-cmd docker socorro webapp bin"
PYTHON_VERSION=$(python --version)


if [[ "${1:-}" == "--fix" ]]; then
    echo ">>> black fix (${PYTHON_VERSION})"
    black $FILES

else
    echo ">>> ruff (${PYTHON_VERSION})"
    ruff $FILES

    echo ">>> black (${PYTHON_VERSION})"
    black --check $FILES

    echo ">>> license check (${PYTHON_VERSION})"
    if [[ -d ".git" ]]; then
        # If the .git directory exists, we can let license-check.py do
        # git ls-files.
        python bin/license-check.py
    else
        # The .git directory doesn't exist, so run it on all the Python
        # files in the tree.
        python bin/license-check.py .
    fi

    echo ">>> eslint (js)"
    cd /app/webapp
    /webapp-frontend-deps/node_modules/.bin/eslint .
fi
