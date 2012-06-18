#!/usr/bin/python
# vim: set shiftwidth=4 tabstop=4 autoindent expandtab:
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os

__all__ = [
    "JsonDB"
]

class JsonDB:
    def __init__(self, filename):
        # filename is in the same directory as this module
        self._filename = os.path.join(os.path.dirname(__file__),
                                      filename + ".json")
        try:
            io = open(self._filename, "r")
        except:
            self._map = {}
            return
        self._map = json.load(io)
        io.close()
    def write(self):
        # FIXME: Shouldn't overwrite if there's a failure writing!
        io = open(self._filename, "w")
        # Keep keys sorted so it diffs well.
        json.dump(self._map, io, indent=2, sort_keys=True)
        io.write("\n")
        io.close()
