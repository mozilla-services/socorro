#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs dependency checks. Must be run from within the crontabber docker container.

set -e

./scripts/socorro crontabber --reset-job=socorro.cron.jobs.monitoring.DependencySecurityCheckCronApp
./scripts/socorro crontabber --job=socorro.cron.jobs.monitoring.DependencySecurityCheckCronApp
