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


if [[ "${1:-}" == "--help" ]]; then
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "  Lint code"
    echo
    echo "Options:"
    echo "  --help  Show this message and exit."
    echo "  --fix   Reformat code."
elif [[ "${1:-}" == "--fix" ]]; then
    echo ">>> ruff fix (${PYTHON_VERSION})"
    ruff format $FILES
    ruff check --fix $FILES
else
    echo ">>> ruff (${PYTHON_VERSION})"
    ruff check $FILES
    ruff format --check $FILES

    echo ">>> license check (${PYTHON_VERSION})"
    if [[ -d ".git" ]]; then
        # If the .git directory exists, we can let license-check do
        # git ls-files.
        license-check
    else
        # The .git directory doesn't exist, so run it on all the Python
        # files in the tree.
        license-check .
    fi

    echo ">>> eslint (js)"
    cd /app/webapp
    /app/webapp/node_modules/.bin/eslint .
fi
