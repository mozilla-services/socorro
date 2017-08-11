#!/bin/bash

# Updates product release and other data in the docker environment.
#
# Usage: docker/run_update_data.sh

set -eo pipefail

# Fetch and update release information for these products (comma-delimited)
PRODUCTS="firefox"

# Fetch release data
docker-compose run crontabber python socorro/cron/crontabber_app.py --job=ftpscraper \
       --crontabber.class-FTPScraperCronApp.products=${PRODUCTS}

# Update featured versions data based on release data
docker-compose run crontabber python socorro/cron/crontabber_app.py --job=featured-versions-automatic \
       --crontabber.class-FeaturedVersionsAutomaticCronApp.products=${PRODUCTS}

# Fetch normalization data for versions we know about
docker-compose run processor python docker/fetch_normalization_data.py
