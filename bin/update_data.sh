#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/update_data.sh
#
# Updates product release and other data in the docker environment.
# This assumes that it is running in the webapp docker container.
#
# Note: This should be called from inside a container.

set -euo pipefail

# Fetch release data (verbosely)
webapp-django/manage.py archivescraper

# Insert data that's no longer on archive.mozilla.org
python ./bin/insert_missing_versions.py
