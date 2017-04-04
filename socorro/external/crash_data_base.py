# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# XXX this is now deprecated and can be deleted.
# See https://bugzilla.mozilla.org/show_bug.cgi?id=1299465

from socorro.lib import (
    MissingArgumentError,
    ResourceNotFound,
    ResourceUnavailable,
)
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib import external_common


class CrashDataBase(object):

    """
    Common implementation of the crash data service for all crashstorage
    schemes.  Any external service that wants to implement a CrashData service
    may subclass from this service.  All they'd have to do is implement the
    'get_storage' method to return an appropriate instance of their own
    crashstorage class.
    """

    def __init__(self, *args, **kwargs):
        super(CrashDataBase, self).__init__()
        self.config = kwargs['config']

    def get_storage(self):
        """derived classes must implement this method to return an instance
        of their own crashstorage class"""
        raise NotImplementedError

    def get(self, **kwargs):
        """Return JSON data of a crash report, given its uuid. """

        filters = [
            ('uuid', None, 'str'),
            ('datatype', None, 'str'),
            ('name', None, 'str')  # only applicable if datatype == 'raw'
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingArgumentError('uuid')

        if not params.datatype:
            raise MissingArgumentError('datatype')

        # get a generic crashstorage instance from whatever external resource
        # is implementing this service.
        store = self.get_storage()

        datatype_method_mapping = {
            'raw': 'get_raw_dump',
            'meta': 'get_raw_crash',
            'processed': 'get_processed',
            'unredacted': 'get_unredacted_processed',
        }

        get = store.__getattribute__(datatype_method_mapping[params.datatype])
        try:
            if params.datatype == 'raw':
                return (
                    get(params.uuid, name=params.name),
                    'application/octet-stream'
                )
            else:
                return get(params.uuid)
        except CrashIDNotFound:
            if params.datatype in ('processed', 'unredacted'):
                # try to fetch a raw crash just to ensure that the raw crash
                # exists.  If this line fails, there's no reason to actually
                # submit the priority job.
                try:
                    store.get_raw_crash(params.uuid)
                except CrashIDNotFound:
                    raise ResourceNotFound(params.uuid)
                raise ResourceUnavailable(params.uuid)
            raise ResourceNotFound(params.uuid)
