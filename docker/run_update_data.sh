#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Updates product release and other data in the docker environment.
# This assumes that it is running in the webapp docker container.

set -eo pipefail

# Fetch release data (verbosely)
webapp-django/manage.py archivescraper

# Insert data that's no longer on archive.mozilla.org
python ./scripts/insert_missing_versions.py
