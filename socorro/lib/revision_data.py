# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Holds utility functions for interacting with Socorro revision data which is generated
during deploys.
"""

import os

from dockerflow.version import get_version as dockerflow_get_version


# This path is hard-coded to the repository root in .circleci/config.yml. This
# file is generated during deploys to server environments.
VERSION_DATA_PATH = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)


def get_version():
    """Returns version.json data from deploys"""
    return dockerflow_get_version(VERSION_DATA_PATH)


def get_version_name():
    """Returns the Socorro version name

    This pulls version data and then returns the best version-y thing available: the
    version, the commit, or "unknown" if there's no version data.

    :returns: string

    """
    version_data = get_version() or {}
    return version_data.get("version") or version_data.get("commit") or "unknown"
