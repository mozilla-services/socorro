#!/bin/bash

# Updates product release and other data in the docker environment.
#
# Usage: docker/run_update_data.sh

set -eo pipefail

# Fetch and update release information for these products (comma-delimited)
PRODUCTS="firefox"
CRONTABBER="docker-compose run crontabber python socorro/cron/crontabber_app.py"


# Fetch release data
${CRONTABBER} --job=ftpscraper \
       --crontabber.class-FTPScraperCronApp.products=${PRODUCTS}

# Update featured versions data based on release data
${CRONTABBER} --job=featured-versions-automatic \
       --crontabber.class-FeaturedVersionsAutomaticCronApp.products=${PRODUCTS}

# Fetch normalization data for versions we know about
docker-compose run processor python docker/fetch_normalization_data.py

# Truncate tables
${CRONTABBER} --job=truncate-partitions

# Create new weekly tables
${CRONTABBER} --job=weekly-reports-partitions
