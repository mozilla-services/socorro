#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs crontabber.

# Run crontabber sleeping 5 minutes between runs
while true; do
    python socorro/cron/crontabber_app.py
    echo "Sleep 5 minutes..."
    sleep 300
done
