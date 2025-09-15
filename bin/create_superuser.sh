#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/create_superuser.sh
#
# Creates a Crash Stats superuser with:
# * username=admin
# * password=admin
# * email=admin@example.com
#
# Note: This is meant to run on the host machine, not in a docker container.

# Create an account in the oidcprovider service container
docker compose up -d oidcprovider
docker compose exec oidcprovider /code/manage.py createuser admin admin admin@example.com

# Creates a superuser account in the Crash Stats webapp corresponding to
# the account just created in the oidcprovider service container.
docker compose run app shell ./webapp/manage.py makesuperuser admin@example.com

echo """Created Crash Stats superuser:
username=admin
password=admin
email=admin@example.com
"""
