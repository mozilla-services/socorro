#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Runs the processor to process whatever crashes are in the queue and
# then quit. It takes a bit, but it will quit. This lets you process
# crashes in a script for automation.

PATH=/stackwalk:${PATH}

${CMDPREFIX} python /app/socorro/processor/processor_app.py \
             --producer_consumer.quit_on_empty_queue \
             --number_of_submissions=all \
             --producer_consumer.number_of_threads=1
