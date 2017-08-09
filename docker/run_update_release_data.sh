#!/bin/bash

# Updates product release data in the docker environment.
#
# Usage: docker/run_update_release_data.sh

set -eo pipefail

# Fetch and update release information for these products (comma-delimited)
PRODUCTS="firefox"

# Update with this frequency
FREQUENCY="1d"

# Fetch release data
python socorro/cron/crontabber_app.py --job=ftpscraper \
       --crontabber.class-FTPScraperCronApp.frequency=${FREQUENCY} \
       --crontabber.class-FTPScraperCronApp.products=${PRODUCTS}

# Update featured versions data based on release data
python socorro/cron/crontabber_app.py --job=featured-versions-automatic \
       --crontabber.class-FeaturedVersionsAutomaticCronApp.frequency=${FREQUENCY} \
       --crontabber.class-FeaturedVersionsAutomaticCronApp.products=${PRODUCTS}
