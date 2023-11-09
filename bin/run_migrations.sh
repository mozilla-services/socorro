#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_migrations.sh
#
# This script runs migrations for Socorro. Run this in a crontabber docker
# container.
#
# Note: This should be called from inside a container.

set -euo pipefail

PRECMD=""

# If SENTRY_DSN is defined, then enable the sentry-cli bash hook which will
# send errors to sentry.
if [ -n "${SENTRY_DSN:-}" ]; then
    echo "SENTRY_DSN defined--enabling sentry."
    PRECMD="python bin/sentry-wrap.py wrap-process --timeout=600 --"
else
    echo "SENTRY_DSN not defined--not enabling sentry."
fi

echo "starting run_migrations.sh: $(date)"

# Run Django migrations
${PRECMD} python webapp/manage.py migrate --no-input

# Insert missing versions
${PRECMD} python bin/insert_missing_versions.py
