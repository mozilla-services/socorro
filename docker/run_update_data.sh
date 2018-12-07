#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Updates product release and other data in the docker environment.
#
# Usage: docker/run_update_data.sh

set -eo pipefail

HOSTUSER=$(id -u):$(id -g)

DC="$(which docker-compose)"

# Fetch release data (verbosely)
${DC} run app shell ./socorro-cmd crontabber --reset-job=archivescraper
${DC} run app shell ./socorro-cmd crontabber --job=archivescraper \
    --crontabber.class-ArchiveScraperCronApp.verbose

# Create ES indexes for the next few weeks
${DC} run app shell ./socorro-cmd create_recent_indices
