# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Settings for running tests. These override settings in base.py."""

from crashstats.settings.base import *  # noqa

SECRET_KEY = "fakekey"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "crashstats",
        "OPTIONS": {"MAX_ENTRIES": 2000},  # Avoid culling during tests
    }
}

# Because this is for running tests, we use the simplest hasher possible.
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

# Remove SessionRefresh middleware so that tests don't need to have a non-expired OIDC token
MIDDLEWARE.remove("mozilla_django_oidc.middleware.SessionRefresh")  # noqa
