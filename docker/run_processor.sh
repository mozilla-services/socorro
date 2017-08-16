#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs the processor.

set -e

# If this was kicked off via docker-compose, then it has a behavior
# configuration already. If it wasn't, then we need to add behavior
# configuration to the environment.
if [[ -z "${PROCESSOR_BEHAVIOR}" ]];
then
    echo "Pulling in processor behavior configuration..."
    CMDPREFIX="/app/bin/build_env.py /app/docker/config/processor.env"
else
    echo "Already have processor behavior configuration..."
    CMDPREFIX=
fi

# Add /stackwalk to the path
PATH=/stackwalk:${PATH}

# Run the processor
${CMDPREFIX} python /app/socorro/processor/processor_app.py
