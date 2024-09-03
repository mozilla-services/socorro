#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: docker/set_up_legacy_es_requirements.sh
#
# Installs legacy elasticsearch requirements to locations shaded by version.
#
# These dependencies are installed separately, relocated, and patched to reference the
# new location (aka shaded), so that they can be installed at the same time as newer versions

# install shaded packages without dependencies
pip install --no-cache-dir --no-deps -r legacy-es-requirements.txt

# move packages to shaded locations
cd /usr/local/lib/python3.11/site-packages/
mv elasticsearch elasticsearch_1_9_0
mv elasticsearch_dsl elasticsearch_dsl_0_0_11

# patch shaded elasticsearch-dsl to use shaded elasticearch
cd elasticsearch_dsl_0_0_11/
sed 's/^from elasticsearch/from elasticsearch_1_9_0/' -i connections.py search.py serializer.py
