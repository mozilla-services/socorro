#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Run scripts for setting up data sources for the local development environment.
# This assumes that it is running in the webapp docker container.

set -e

# Drop and re-create the breakpad database with tables, stored procedures,
# types, indexes, and keys; also bulk-loads static data for some lookup tables
/app/bin/setup_postgres.sh

# Delete and create local S3 buckets
/app/bin/recreate_s3_buckets.sh

# Delete and create Elasticsearch indices
/app/socorro-cmd es delete
/app/socorro-cmd es create

# Delete and create SQS queues
/app/socorro-cmd sqs delete-all
/app/socorro-cmd sqs create-all

# Initialize the cronrun bookkeeping for all configured jobs to success
/app/webapp-django/manage.py cronmarksuccess all
