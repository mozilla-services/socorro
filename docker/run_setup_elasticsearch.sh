#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Sets up Elasticsearch.

cd /app/scripts/

# FIXME(willkg): Make this idempotent so that running it after it's already been
# run doesn't affect anything.

echo "Setting up Elasticsearch indexes..."
python setup_supersearch_app.py
