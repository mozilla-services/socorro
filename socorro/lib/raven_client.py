# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from pkg_resources import resource_string

import raven

# When socorro is installed (python setup.py install), it will create
# a file in site-packages for socorro called "socorro/socorro_revision.txt".
# If this socorro was installed like that, let's pick it up and use it.
try:
    SOCORRO_REVISION = resource_string('socorro', 'socorro_revision.txt').strip()
except IOError:
    SOCORRO_REVISION = None


def get_client(dsn, **kwargs):
    kwargs['dsn'] = dsn
    if not kwargs.get('release') and SOCORRO_REVISION:
        kwargs['release'] = SOCORRO_REVISION
    return raven.Client(**kwargs)
