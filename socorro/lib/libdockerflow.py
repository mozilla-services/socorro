# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Holds utility functions for interacting with Socorro revision data which is generated
during deploys.
"""

import json
from pathlib import Path


def get_version_info(basedir):
    """Given a basedir, retrieves version information for this deploy.

    :arg str basedir: the path of the base directory where ``version.json``
        exists

    :returns: version info as a dict or an empty dict

    """
    path = Path(basedir) / "version.json"
    if not path.exists():
        return {}

    try:
        data = path.read_text()
        return json.loads(data)
    except (OSError, json.JSONDecodeError):
        return {}


def get_release_name(basedir):
    """Return a friendly name for the release that is running

    This pulls version data and then returns the best version-y thing available: the
    version, the commit, or "unknown" if there's no version data.

    :returns: string

    """
    version_info = get_version_info(basedir)
    version = version_info.get("version", "none")
    commit = version_info.get("commit")
    commit = commit[:8] if commit else "unknown"
    return f"{version}:{commit}"
