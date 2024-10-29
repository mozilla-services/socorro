#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_symbolsserver.sh
#
# Runs a local symbols server for the local dev environment.
#
# Note: This is not a production-ready server. It's intended only for
# debugging.

set -euxo pipefail

SYMBOLS_PATH=/app/symbols
PORT=8070

if [ ! -d "${SYMBOLS_PATH}" ]
then
    mkdir -p "${SYMBOLS_PATH}"
fi

echo "Running local symbols server at ${SYMBOLS_PATH} ..."
exec python -m http.server --directory "${SYMBOLS_PATH}" --bind 0.0.0.0 "${PORT}"
