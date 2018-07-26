#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Updates product release and other data in the docker environment.
#
# Usage: docker/run_update_data.sh

set -eo pipefail

HOSTUSER=$(id -u):$(id -g)

# Fetch and update release information for these products (comma-delimited)
PRODUCTS="firefox,mobile"
CRONTABBERCMD="./socorro/cron/crontabber_app.py"


# Fetch release data -- do it as the user so it can cache things, but reset
# the ftpscraper job first
docker-compose run crontabber ${CRONTABBERCMD} --reset-job=ftpscraper
docker-compose run -u "${HOSTUSER}" crontabber ${CRONTABBERCMD} \
               --job=ftpscraper \
               --crontabber.class-FTPScraperCronApp.products=${PRODUCTS}

# Update featured versions data based on release data
docker-compose run crontabber ${CRONTABBERCMD} --reset-job=featured-versions-automatic
docker-compose run crontabber ${CRONTABBERCMD} --job=featured-versions-automatic \
              --crontabber.class-FeaturedVersionsAutomaticCronApp.products=${PRODUCTS}

# Create ES indexes for the next few weeks
docker-compose run processor socorro/external/es/create_recent_indices_app.py
