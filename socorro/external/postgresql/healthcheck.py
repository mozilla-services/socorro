# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class Healthcheck(object):
    """Actually not related to Postgres in any way. This just need to
    exist in the middleware_app and the socorro.external.postgres is
    the default implementation namespace."""
    def __init__(self, *args, **kwargs):
        pass

    def get(self, **kwargs):
        return True
