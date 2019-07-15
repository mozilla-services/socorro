#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Replaces the original run script at:
# https://github.com/mozilla-parsys/docker-test-mozilla-django-oidc/blob/master/testprovider/bin/run.sh
# Changes:
# - Print commnds as the execute
# - Optionally creates a user, if specified in the environment.

set -x

python manage.py migrate --noinput
python manage.py loaddata fixtures.json

if [ -n "$OIDC_USERNAME" ] && [ -n "$OIDC_PASSWORD" ] && [ -n "$OIDC_EMAIL" ]
then
    # Command must start on the first line, required by ./manage.py shell
    ./manage.py shell -c "\
from django.contrib.auth.models import User; \
user, _ = User.objects.get_or_create(email=\"${OIDC_EMAIL}\", defaults={\"username\": \"${OIDC_USERNAME}\"}); \
user.set_password(\"${OIDC_PASSWORD}\"); \
user.save()"
fi

python manage.py runserver 0.0.0.0:8080
