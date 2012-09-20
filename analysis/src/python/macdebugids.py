#!/usr/bin/python
# vim: set shiftwidth=4 tabstop=4 autoindent expandtab:
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import jsondb
import sys

__all__ = [
    "info_for_id"
]

class LibraryInfoMap(jsondb.JsonDB):
    def put(self, name, id, description):
        namemap = self._map.setdefault(name, {})
        namemap[id] = description
    def get(self, libname, id):
        map = self._map
        if not libname in map:
            return None
        namemap = map[libname]
        if not id in namemap:
            return None
        return namemap[id]

local_db = LibraryInfoMap("macdebugids")

def info_for_id(libname, id):
    return local_db.get(libname, id)

# When executed directly...
if __name__ == '__main__':
    if len(sys.argv) == 1:
        # prompt for an addition to the local database.
        sys.stdout.write("Library Name: ")
        name = sys.stdin.readline().rstrip("\n")
        sys.stdout.write("Library Debug ID: ")
        id = sys.stdin.readline().rstrip("\n")
        sys.stdout.write("Description: ")
        description = sys.stdin.readline().rstrip("\n")
        local_db.put(name, id, description)
        local_db.write()
    else:
        raise StandardError("unexpected arguments")
