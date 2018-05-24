#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Installs sentry-cli.

set -v -e -x

# Comes from https://sentry.io/get-cli/
SENTRY_URL=https://github.com/getsentry/sentry-cli/releases/download/1.32.0/sentry-cli-Linux-x86_64

# The final sentry-cli binary
SENTRY_BIN=/usr/bin/sentry-cli

curl -L "${SENTRY_URL}" -o "${SENTRY_BIN}"
chmod 755 "${SENTRY_BIN}"
