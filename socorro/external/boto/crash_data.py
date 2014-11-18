# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# this is a temporary hack to coerse the middleware to talk to boto S3
# instead of HBase.

from socorro.external.crash_data_base import CrashDataBase


class CrashData(CrashDataBase):
    """
    Implement the /crash_data service with HBase.
    """
    def get_storage(self):
        # why does this say hbase? Aren't we a botos3 module?
        # yes, this seems odd, but the second generation middleware was
        # built hard coded to using specific resources, though within those
        # resources, configman was used to get config details for that
        # resource.  Now that we're moving away from HBase, we can swap
        # out the implementation of the hard coded HBase section with details
        # from its replacement: boto S3.  So all indications in the code
        # are that it is using HBase, but configuration has replaced the
        # implementation details with boto S3.
        return self.config.hbase.hbase_class(self.config.hbase)

