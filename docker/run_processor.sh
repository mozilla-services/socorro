#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs the processor.

# Add /stackwalk to the path
PATH=/stackwalk:${PATH}

# Run the processor
python /app/socorro/processor/processor_app.py
