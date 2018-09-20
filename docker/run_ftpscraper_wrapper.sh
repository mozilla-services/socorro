#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Checks the cached ftpscraper log and if it's less than 7 days old, replays it
# which is super duper fast.

set -eo pipefail

DC="$(which docker-compose)"

# Fetch and update release information for these products (comma-delimited).
PRODUCTS="firefox,mobile"
CRONTABBERCMD="./socorro-cmd crontabber"
CACHEDIR="./.cache"
CACHEFILE="${CACHEDIR}/ftpscraper.log"

# If the cache file exists...
if [[ -e "${CACHEFILE}" ]]; then
    FILEMODDATE=$(date -r ${CACHEFILE} '+%s')
    NOW=$(date +%s)
    FILEAGE=$(((NOW - FILEMODDATE) / 60 / 60 / 24))

    # And it's less than a week old... replay.
    if [[ ${FILEAGE} -lt 7 ]]; then
        echo "Found recent (${FILEAGE}d) ftpscraper log--replaying...."
        ${DC} run app shell ./socorro-cmd replay_ftpscraper "${CACHEFILE}"
        exit
    fi
fi

# Create the cachedir if it doesn't exist.
if [[ ! -e "${CACHEDIR}" ]]; then
    mkdir "${CACHEDIR}"
fi

${DC} run app shell ${CRONTABBERCMD} --reset-job=ftpscraper
${DC} run app shell bash -c "${CRONTABBERCMD} --job=ftpscraper --crontabber.class-FTPScraperCronApp.products=${PRODUCTS} |& tee ${CACHEFILE}"
