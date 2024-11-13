#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_postdeploy.sh
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
    PRECMD="sentry-wrap wrap-process --timeout=600 --"
else
    echo "SENTRY_DSN not defined--not enabling sentry."
fi

echo "$(date): run migrations"
${PRECMD} /app/bin/run_migrations.sh

echo "$(date): upload telemetry schema"
${PRECMD} python /app/bin/upload_telemetry_schema.py
