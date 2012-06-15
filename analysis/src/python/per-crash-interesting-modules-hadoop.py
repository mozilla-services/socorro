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
import addonids
import macdebugids
import re

op = OptionParser()

op.add_option("-v", "--versions",
              action="store_true", dest="show_versions",
              help="Show data on module versions")
op.add_option("-o", "--by-os-version",
              action="store_true", dest="by_os_version",
              help="Group reports by *version* of operating system")
op.add_option("-a", "--addons",
              action="store_true", dest="addons",
              help="Tabulate addons (rather than modules)")
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
                                  "module_counts": {} })
        osys["count"] = count
    elif len(key_splits) == 2:
        osname = key_splits[0]
        sigreason = key_splits[1]
        osys = osyses.setdefault(osname,
                                { "count": 0,
                                  "signatures": {},
                                  "module_counts": {} })
        signature = osys["signatures"].setdefault(sigreason,
                                                  { "count": 0,
                                                    "module_counts": {} })
        signature["count"] = count
    elif len(key_splits) == 3:
        osname = key_splits[0]
        sigreason = key_splits[1]
        info_splits = info_pattern.split(key_splits[2])
        libname = info_splits[0]
        version = None
        if len(info_splits) == 2:
            version = info_splits[1]

        osys = osyses.setdefault(osname,
                                { "count": 0,
                                  "signatures": {},
                                  "module_counts": {} })

        if sigreason == '' and libname != '':
            modinfo = osys["module_counts"].setdefault(libname,
                                                       { "count": 0,
                                                         "version_counts": {} })
            if version == None:
                modinfo["count"] = count
            else:
                modinfo["version_counts"][version] = count
        elif sigreason != '' and libname != '':
            signature = osys["signatures"].setdefault(sigreason,
                                                      { "count": 0,
                                                        "module_counts": {} })
            modinfo = signature["module_counts"].setdefault(libname,
                                                            { "count": 0,
                                                              "version_counts": {} })
            if version == None:
                modinfo["count"] = count
            else:
                modinfo["version_counts"][version] = count

results.close()

# For each stack signature for which we have at least 10 crashes, print
# out modules at least 5% above baseline.
MIN_CRASHES = 10
MIN_BASELINE_DIFF = 0.05
sorted_osyses = osyses.keys()
sorted_osyses.sort()
for osname in sorted_osyses:
   osys = osyses[osname]
   print
   print osname
   sorted_signatures = [sig for sig in osys["signatures"].items() \
                          if sig[1]["count"] >= MIN_CRASHES]
   sorted_signatures.sort(key=lambda tuple: tuple[1]["count"], reverse=True)
   for signame, sig in sorted_signatures:
       print "  %s (%d crashes)" % (signame, sig["count"])
       modules = [ {
                     "libname": libname,
                     "in_sig_count": modinfo["count"],
                     "in_sig_ratio": float(modinfo["count"]) / sig["count"],
                     "in_sig_versions": modinfo["version_counts"],
                     "in_os_count": osys["module_counts"][libname]["count"],
                     "in_os_ratio":
                       float(osys["module_counts"][libname]["count"]) /
                       osys["count"],
                     "in_os_versions":
                       osys["module_counts"][libname]["version_counts"]
                   }
                   for libname, modinfo in sig["module_counts"].items()]
       modules = [ module for module in modules
                     if module["in_sig_ratio"] - module["in_os_ratio"] >=
                        MIN_BASELINE_DIFF ]
       modules.sort(key = lambda module: module["in_sig_ratio"] -
                                         module["in_os_ratio"],
                    reverse = True)
       for module in modules:
           libname = module["libname"]
           if options.addons:
               info = addonids.info_for_id(libname)
               if info is not None:
                   libname = libname + u" ({0}, {1})".format(info.name,
                                                             info.url)
           if options.show_versions and len(module["in_os_versions"]) == 1:
               onlyver = module["in_os_versions"].keys()[0]
               if osname.startswith("Mac OS X"):
                   info = macdebugids.info_for_id(libname, onlyver)
                   if info is not None:
                       onlyver = onlyver + "; " + info
               if (onlyver != ""):
                   libname = libname + " (" + onlyver + ")"
           print u"    {0:3d}% ({1:d}/{2:d}) vs. {3:3d}% ({4:d}/{5:d}) {6}"\
                   .format(int(round(module["in_sig_ratio"] * 100)),
                           module["in_sig_count"],
                           sig["count"],
                           int(round(module["in_os_ratio"] * 100)),
                           module["in_os_count"],
                           osys["count"],
                           libname).encode("UTF-8")
           if options.show_versions and len(module["in_os_versions"]) != 1:
               versions = module["in_os_versions"].keys()
               versions.sort()
               for version in versions:
                   sig_ver_count = module["in_sig_versions"].get(version, 0)
                   os_ver_count = module["in_os_versions"][version]
                   if osname.startswith("Mac OS X"):
                       info = macdebugids.info_for_id(libname, version)
                       if info is not None:
                           version = version + " (" + info + ")"
                   print u"        {0:3d}% ({1:d}/{2:d}) vs. {3:3d}% ({4:d}/{5:d}) {6}"\
                         .format(int(round(float(sig_ver_count) /
                                             sig["count"] * 100)),
                                 sig_ver_count,
                                 sig["count"],
                                 int(round(float(os_ver_count) /
                                             osys["count"] * 100)),
                                 os_ver_count,
                                 osys["count"],
                                 version).encode("UTF-8")
       print
   print
