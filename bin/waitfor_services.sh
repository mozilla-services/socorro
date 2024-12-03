#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/waitfor_services.sh
#
# Waits for dev services to start up.
#
# Note: This should be called from inside a container.

set -euo pipefail

waitfor --verbose --conn-only "${DATABASE_URL}"
waitfor --verbose "${LEGACY_ELASTICSEARCH_URL}"
waitfor --verbose "http://${PUBSUB_EMULATOR_HOST}"
waitfor --verbose "${STORAGE_EMULATOR_HOST}/storage/v1/b"
waitfor --verbose --codes={200,404} "${SENTRY_DSN}"
# wait for this last because it's slow to start
waitfor --verbose --timeout=30 "${ELASTICSEARCH_URL}"
