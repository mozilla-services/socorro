#!/bin/bash

# Updates product release and other data in the docker environment.
#
# Usage: docker/run_update_data.sh

set -eo pipefail

HOSTUSER=$(id -u):$(id -g)

# The assumption is that you're running this from /app inside the container
CACHEDIR=/app/.cache/ftpscraper

# Fetch and update release information for these products (comma-delimited)
PRODUCTS="firefox,mobile"
CRONTABBERCMD="./socorro/cron/crontabber_app.py"


# Fetch release data -- do it as the user so it can cache things, but reset
# the ftpscraper job first
docker-compose run crontabber ${CRONTABBERCMD} --reset-job=ftpscraper
docker-compose run -u "${HOSTUSER}" crontabber ${CRONTABBERCMD} \
               --job=ftpscraper \
               --crontabber.class-FTPScraperCronApp.cachedir=${CACHEDIR} \
               --crontabber.class-FTPScraperCronApp.products=${PRODUCTS}

# Update featured versions data based on release data
docker-compose run crontabber ${CRONTABBERCMD} --job=featured-versions-automatic \
              --crontabber.class-FeaturedVersionsAutomaticCronApp.products=${PRODUCTS}

# Create ES indexes for the next few weeks
docker-compose run processor socorro/external/es/create_recent_indices_app.py
