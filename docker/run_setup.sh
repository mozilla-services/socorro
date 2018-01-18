#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Run scripts for setting up data sources for the local development environment.
# This assumes that it is running in the webapp docker container.

/app/docker/run_setup_postgres.sh
/app/docker/run_recreate_s3_buckets.sh
/app/scripts/socorro clear_es_indices
