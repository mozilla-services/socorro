# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Holds utility functions for interacting with Socorro revision data
which is generated during deploys.
"""

import json
import os


# This path is hard-coded to the repository root in .circleci/config.yml. This
# file is generated during deploys to server environments.
REVISION_DATA_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "version.json"
)


def get_revision_data():
    """Returns revision data

    During deploys, the deploy scripts generate a ``version.json`` file
    containing revision information. This information includes the following:

    * commit
    * version
    * source
    * build

    If the file is there, this function will return a dict with that. If
    not--as in the case of a local development environment--then this function
    will return an empty dict.

    :returns: dict of revision data or empty dict if there's no revision data
        file

    """
    if os.path.exists(REVISION_DATA_PATH):
        with open(REVISION_DATA_PATH, "r") as fp:
            return json.load(fp)
    return {}


def get_version(revision_data=None):
    """Returns the Socorro version

    This pulls revision data and then returns the best version-y thing
    available: the tag, the commit, or "unknown" if there's no revision
    data.

    :arg revision_data: revision data, or None to fetch from disk
    :returns: string

    """
    if revision_data is None:
        revision_data = get_revision_data()
    return revision_data.get("version") or revision_data.get("commit") or "unknown"
