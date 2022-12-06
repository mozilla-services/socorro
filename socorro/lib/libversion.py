# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import suppress

import semver


class VersionParseError(Exception):
    """Raised if the version isn't parseable."""


def generate_semver(version):
    """Convert a version to semver.

    This converts the version string to a semver that (ab)uses the prerelease section to
    denote the channel and in doing that, sorts Firefox and Fenix versions correctly.

    :param version: the version string

    :returns: a semver.VersionInfo

    :raises VersionParseError: if the version isn't parseable

    """
    if not isinstance(version, str):
        raise VersionParseError("version is not a str.")

    # Try to parse it as a semver. This covers versions that are valid semver already.
    with suppress(ValueError):
        semver_version = semver.VersionInfo.parse(version)
        if semver_version.prerelease is None:
            # Need to add this so that 68.0.0 (release) sorts correctly with
            # 68.0.0esr--ESR versions sort after release versions
            semver_version = semver_version.replace(prerelease="release.rc.999")
        return semver_version

    # If it's not semver, then it's probably a Firefox version number, so parse that and
    # convert it to a semver VersionInfo

    orig_version = version
    prerelease = []

    try:
        if "rc" in version:
            version, rc = version.split("rc")
            prerelease.insert(0, "rc.%s" % rc)
        else:
            # If it's not a release candidate, we add rc.999 so actual releases sort
            # after release candidates
            prerelease.insert(0, "rc.999")

        if "a" in version:
            version, num = version.split("a")
            # All "alphas" are nightly channel and get alpha.1 as a prerelease
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
            # Use xsr here because it sorts alphabetically like this: alpha, beta,
            # release, xsr
            prerelease.insert(0, "xsr")

        else:
            # Need to add "release" so that it sorts correctly with alpha, beta,
            # and xsr
            prerelease.insert(0, "release")

        # Do this so it's easier to build the VersionInfo instance
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
