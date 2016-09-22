#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
from distutils.version import Version


class FirefoxVersion(Version):
    """Version numbering for Firefox.

    The following are valid version numbers (shown in the order that
    would be obtained by sorting according to the supplied cmp function):

    3.6 3.6.0 (these two are equivalent)
    4.0
    5.0a1
    5.0(beta)
    5.0b3
    5.0pre
    5.0
    6.0.1
    17.0
    17.0esr (newer than 17.0)

    """

    version_re = re.compile(r'^(\d+) \. (\d+) (\. (\d+))?'
                            r'((a|b|pre|\(beta\)|esr)(\d*))?$',
                            re.VERBOSE)

    def parse(self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError('invalid version number "%s"' % vstring)

        (major, minor, patch, prerelease, prerelease_num) = \
            match.group(1, 2, 4, 6, 7)

        self.version = tuple(map(int, [major, minor, patch or 0]))

        self.prerelease = None
        self.postrelease = None

        if prerelease == "esr":
            self.postrelease = "esr"

        elif prerelease:
            try:
                self.prerelease = (prerelease, int(prerelease_num))
            except ValueError:
                self.prerelease = (prerelease, None)

    def __str__(self):
        if self.version[2] == 0:
            vstring = '.'.join(map(str, self.version[0:2]))
        else:
            vstring = '.'.join(map(str, self.version))

        if self.postrelease:
            vstring += self.postrelease

        if self.prerelease:
            prerelease, pr_num = self.prerelease
            vstring += prerelease + (str(pr_num) if pr_num else '')

        return vstring

    def __repr__(self):
        return 'FirefoxVersion ("%s")' % str(self)

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = FirefoxVersion(other)

        compare = cmp(self.version, other.version)

        # Numeric versions don't match, so just return the cmp() result.
        if compare:
            return compare

        # The versions are the same, so compare the "postreleases".

        if self.postrelease and not other.postrelease:
            return 1
        elif not self.postrelease and other.postrelease:
            return -1
        # If there is ever another postrelease, logic will need to be
        # added here to provide comparison for them.

        # The postreleases are the same, so compare the "prereleases".

        # case 1: neither has prerelease; they're equal
        # case 2: self has prerelease, other doesn't; other is greater
        # case 3: self doesn't have prerelease, other does: self is greater
        # case 4: both have prerelease: must compare them!

        if not self.prerelease and not other.prerelease:
            return 0
        elif self.prerelease and not other.prerelease:
            return -1
        elif not self.prerelease and other.prerelease:
            return 1
        else:
            prereleases = ('a', '(beta)', 'b', 'pre')
            prerelease_compare = cmp(prereleases.index(self.prerelease[0]),
                                     prereleases.index(other.prerelease[0]))
            if not prerelease_compare:
                if self.prerelease[1] is None and other.prerelease[1] is not None:
                    return 1
                elif self.prerelease[1] is not None and other.prerelease[1] is None:
                    return -1
                else:
                    return cmp(self.prerelease[1], other.prerelease[1])
            else:
                return prerelease_compare
