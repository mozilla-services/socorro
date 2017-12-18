# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.lib import external_common, MissingArgumentError, BadArgumentError
from socorro.external.boto.crashstorage import (
    BotoS3CrashStorage,
    CrashIDNotFound,
)
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


class SimplifiedCrashData(BotoS3CrashStorage):
    """The difference between this and the base CrashData class is that
    this one only makes the get() and if it fails it does NOT
    try to put the crash ID back into the priority jobs queue.
    Also, it returns a python dict instead of a DotDict which
    makes this easier to work with from the webapp's model bridge.
    """

    def __init__(self, *args, **kwargs):
        super(SimplifiedCrashData, self).__init__(*args, **kwargs)
        # Forcibly set this to override the default in the base
        # crash storage class for boto. We're confident that at this
        # leaf point we want to NOT return a DotDict but just a plain
        # python dict.
        self.config.json_object_hook = dict

    def get(self, **kwargs):
        """Return JSON data of a crash report, given its uuid. """
        filters = [
            ('uuid', None, str),
            ('datatype', None, str),
            ('name', None, str)  # only applicable if datatype == 'raw'
        ]
        params = external_common.parse_arguments(filters, kwargs, modern=True)

        if not params.uuid:
            raise MissingArgumentError('uuid')

        if not params.datatype:
            raise MissingArgumentError('datatype')

        datatype_method_mapping = {
            'raw': 'get_raw_dump',
            'meta': 'get_raw_crash',
            'processed': 'get_processed',
            'unredacted': 'get_unredacted_processed',
        }
        if params.datatype not in datatype_method_mapping:
            raise BadArgumentError(params.datatype)
        get = self.__getattribute__(datatype_method_mapping[params.datatype])
        try:
            if params.datatype == 'raw':
                return get(params.uuid, name=params.name)
            else:
                return get(params.uuid)
        except CrashIDNotFound as cidnf:
            self.config.logger.error('%s not found: %s' % (params.datatype, cidnf))
            # The CrashIDNotFound exception that happens inside the
            # crashstorage is too revealing as exception message
            # contains information about buckets and prefix keys.
            # Re-wrap it here so the message is just the crash ID.
            raise CrashIDNotFound(params.uuid)
