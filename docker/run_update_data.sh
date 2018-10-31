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

# Fetch and update release information for these products (comma-delimited)
PRODUCTS="firefox,mobile"
CRONTABBERCMD="./socorro/cron/crontabber_app.py"


# Fetch release data -- use the ftpscraper wrapper which will use cached
# data if it's available and run ftpscraper as a 20-minute last resort
./docker/run_ftpscraper_wrapper.sh

# Update featured versions data based on release data
${DC} run app shell ${CRONTABBERCMD} --reset-job=featured-versions-automatic
${DC} run app shell ${CRONTABBERCMD} --job=featured-versions-automatic \
    --crontabber.class-FeaturedVersionsAutomaticCronApp.products=${PRODUCTS}

# Create ES indexes for the next few weeks
${DC} run app shell ./socorro-cmd create_recent_indices
