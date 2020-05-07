# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import semver


class VersionParseError(Exception):
    """Raised if the version isn't parseable"""


def generate_semver(version):
    """Convert a version to semver.

    This converts to a semver that (ab)uses the prerelease section to denote the channel
    and in doing that, sorts Firefox versions correctly.

    :param version: the version string

    :returns: a semver.VersionInfo

    :raises VersionParseError: if the version isn't parseable

    """
    if not isinstance(version, str):
        raise VersionParseError("version is not a str.")

    try:
        semver_version = semver.VersionInfo.parse(version)
        if semver_version.prerelease is None:
            semver_version = semver_version.replace(prerelease="release.rc.999")
        return semver_version
    except ValueError:
        pass

    orig_version = version
    prerelease = []

    try:
        if "rc" in version:
            version, rc = version.split("rc")
            prerelease.insert(0, "rc.%s" % rc)
        else:
            prerelease.insert(0, "rc.999")

        if "a" in version:
            version, num = version.split("a")
            prerelease.insert(0, "alpha.1")

        elif "b" in version:
            version, num = version.split("b")
            # Handle the 62.0b case which is a superset of betas
            if not num:
                prerelease.insert(0, "beta")
            else:
                prerelease.insert(0, "beta.%s" % num)

        elif "esr" in version:
            version = version.replace("esr", "")
            # NOTE(willkg): use xsr here because it sorts alphabetically
            # like this: alpha, beta, release, xsr
            prerelease.insert(0, "xsr")

        else:
            prerelease.insert(0, "release")

        version = [int(part) for part in version.split(".")]
        while len(version) < 3:
            version.append(0)

        return semver.VersionInfo(
            **{
                "major": version[0],
                "minor": version[1],
                "patch": version[2],
                "prerelease": ".".join(prerelease),
            }
        )

    except (ValueError, IndexError, TypeError) as exc:
        raise VersionParseError(
            "Version %s does not parse: %s" % (repr(orig_version), str(exc))
        )
