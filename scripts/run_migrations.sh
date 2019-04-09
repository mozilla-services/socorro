#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This script runs migrations for Socorro. Run this in a crontabber docker
# container.

set -e

# If RAVEN_DSN is defined, then define SENTRY_DSN and evoke the sentry-cli bash
# hook which will send errors to sentry.
if [ -n "${RAVEN_DSN}" ]; then
    echo "RAVEN_DSN defined--enabling sentry."
    export SENTRY_DSN=${RAVEN_DSN}
    eval "$(/webapp-frontend-deps/node_modules/.bin/sentry-cli bash-hook)"
else
    echo "RAVEN_DSN not defined--not enabling sentry."
fi

# Get a datestamp
date

# Run Django migrations
python webapp-django/manage.py migrate --no-input

# Insert missing versions
python scripts/insert_missing_versions.py
