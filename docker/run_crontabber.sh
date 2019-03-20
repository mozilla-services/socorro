#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs crontabber.

set -e

# Run crontabber sleeping 5 minutes between runs
while true
do
    # NOTE(willkg): We don't want crontabber to exit weird and then have that
    # kill the container, but this is a lousy thing to do.
    ./socorro-cmd crontabber || true
    # NOTE(willkg): We are in a period of time where there are multiple
    # crontabbers.
    ./webapp-django/manage.py cron || true
    echo "Sleep 5 minutes..."
    sleep 300
done
