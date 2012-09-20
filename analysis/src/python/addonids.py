#!/usr/bin/python
# vim: set shiftwidth=4 tabstop=4 autoindent expandtab:
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import jsondb
import sys
import re

__all__ = [
    "info_for_id"
]

class AddonInfoMap(jsondb.JsonDB):
    def put(self, id, name, url):
        self._map[id] = { "name": name, "url": url }
    def get(self, id):
        map = self._map
        if not id in map:
            return None
        entry = map[id]
        return AddonInfo(name=entry["name"], url=entry["url"])

class AMOAddonInfoMap(AddonInfoMap):
    def get(self, id):
        if not id in self._map:
            self.check_AMO()
        return AddonInfoMap.get(self, id)
    def check_AMO(self):
        # store result whether it's "None" or not
        # FIXME: WRITE ME
        pass

class AddonInfo:
    def __init__(self, name, url):
        self.name = name
        self.url = url

local_db = AddonInfoMap("addonids-local")
amo_db = AMOAddonInfoMap("addonids-amo")

def info_for_id(id):
    return local_db.get(id) or amo_db.get(id)

# When executed directly...
if __name__ == '__main__':
    if len(sys.argv) == 1:
        # prompt for an addition to the local database.
        sys.stdout.write("Addon ID: ")
        id = sys.stdin.readline().rstrip("\n")
        sys.stdout.write("Name: ")
        name = sys.stdin.readline().rstrip("\n")
        sys.stdout.write("Homepage: ")
        url = sys.stdin.readline().rstrip("\n")
        local_db.put(id, name, url)
        local_db.write()
    elif len(sys.argv) == 2 and sys.argv[1] == "-i":
        # or, with -i, import the AMO one
        io = open("amo-ids.txt", "r")
        for line in io:
            # Sometimes the last field is \N instead of a string
            line = re.sub(r'\\N$', r'""', line)
            [id, number, name] = json.loads("[" + line + "]")
            if len(id) > 0:
                url = "https://addons.mozilla.org/addon/" + str(number)
                amo_db.put(id, name, url)
        io.close()
        amo_db.write()
    else:
        raise StandardError("unexpected arguments")
