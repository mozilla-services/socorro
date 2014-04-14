# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.crash_data_base import CrashDataBase


class CrashData(CrashDataBase):
    """
    Implement the /crash_data service with HBase.
    """
    def get_storage(self):
        return self.config.hbase.hbase_class(self.config.hbase)

