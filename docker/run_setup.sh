#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Run scripts for setting up data sources for the local development environment.
# This assumes that it is running in the webapp docker container.

# Drop and re-create the breakpad database with tables, stored procedures,
# types, indexes, and keys; also bulk-loads static data for some lookup tables
/app/docker/run_setup_postgres.sh

# Drop and re-create local S3 buckets
/app/docker/run_recreate_s3_buckets.sh

# Delete all Elasticsearch indices
/app/socorro/external/es/clear_indices_app.py

# Initialize the crontabber bookkeeping for all configured jobs to success
/app/socorro/cron/crontabber_app.py --mark-success=all
