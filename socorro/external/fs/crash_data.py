# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.middleware.crash_data import CrashDataBase


class CrashData(CrashDataBase):

    """
    Implement the /crash_data service with the file system.
    """

    def get_storage(self):
        return self.config.filesystem.filesystem_class(self.config.filesystem)
