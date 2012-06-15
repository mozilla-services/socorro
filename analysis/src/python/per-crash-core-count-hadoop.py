#!/usr/bin/python
# vim: set shiftwidth=4 tabstop=4 autoindent expandtab:
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is find-interesting-modules.py.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   L. David Baron <dbaron@dbaron.org>, Mozilla Corporation (original author)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

from optparse import OptionParser
import re

op = OptionParser()

op.add_option("-o", "--by-os-version",
              action="store_true", dest="by_os_version",
              help="Group reports by *version* of operating system")
op.add_option("-c", "--condense",
              action="store_true", dest="condense",
              help="Condense signatures in modules we don't have symbols for")

(options, args) = op.parse_args();
if len(args) != 1:
    op.error("wrong number of arguments")

# For each operating system, accumulate total and per-stack-signature
# counts of the total number of crashes and the number of crashes in
# which each module was found.
tab_pattern = re.compile(u"\t")
key_pattern = re.compile(u"\u0001")
info_pattern = re.compile(u"\u0002");

osyses = {}
results = open(args[0], "r")
for line in results:
    kv = tab_pattern.split(line)
    if len(kv) != 2:
        print "Bad line: %s" % (line)
        continue

    key_splits = key_pattern.split(kv[0])
    count = long(kv[1])
    if len(key_splits) == 1:
        osname = key_splits[0]
        osys = osyses.setdefault(osname,
                                { "count": 0,
                                  "signatures": {},
                                  "core_counts": {} })
        osys["count"] = count
    elif len(key_splits) == 2:
        osname = key_splits[0]
        sigreason = key_splits[1]
        osys = osyses.setdefault(osname,
                                { "count": 0,
                                  "signatures": {},
                                  "core_counts": {} })
        signature = osys["signatures"].setdefault(sigreason,
                                                  { "count": 0,
                                                    "core_counts": {} })
        signature["count"] = count
    elif len(key_splits) == 3:
        osname = key_splits[0]
        sigreason = key_splits[1]
        family, cores = info_pattern.split(key_splits[2])
        core_info = "%s with %s cores" % (family, cores)

        osys = osyses.setdefault(osname,
                                { "count": 0,
                                  "signatures": {},
                                  "core_counts": {} })

        if sigreason == '':
            osys["core_counts"][core_info] = count
        else:
            signature = osys["signatures"].setdefault(sigreason,
                                                      { "count": 0,
                                                        "core_counts": {} })
            signature["core_counts"][core_info] = count

results.close()

infostr_re = re.compile("^(.*) with (\d+) cores$")
def cmp_infostr(x, y):
    (familyx, coresx) = infostr_re.match(x).groups()
    (familyy, coresy) = infostr_re.match(y).groups()
    if familyx != familyy:
        return cmp(familyx, familyy);
    return cmp(int(coresx), int(coresy))

# For each stack signature for which we have at least 10 crashes, print
# out cores table.
MIN_CRASHES = 10
sorted_osyses = osyses.keys()
sorted_osyses.sort()
for osname in sorted_osyses:
    osys = osyses[osname]
    print
    print osname
    sorted_signatures = [sig for sig in osys["signatures"].items() \
                           if sig[1]["count"] >= MIN_CRASHES]
    sorted_signatures.sort(key=lambda tuple: tuple[1]["count"], reverse=True)
    sorted_cores = osys["core_counts"].keys()
    sorted_cores.sort(cmp = cmp_infostr)
    for signame, sig in sorted_signatures:
        print "  %s (%d crashes)" % (signame, sig["count"])
        for cores in sorted_cores:
            in_sig_count = sig["core_counts"].get(cores, 0)
            in_sig_ratio = float(in_sig_count) / sig["count"]
            in_os_count = osys["core_counts"][cores]
            in_os_ratio = float(in_os_count) / osys["count"]
            print u"    {0:3d}% ({1:d}/{2:d}) vs. {3:3d}% ({4:d}/{5:d}) {6}"\
                    .format(int(round(in_sig_ratio * 100)),
                            in_sig_count,
                            sig["count"],
                            int(round(in_os_ratio * 100)),
                            in_os_count,
                            osys["count"],
                            cores).encode("UTF-8")
        print
    print
