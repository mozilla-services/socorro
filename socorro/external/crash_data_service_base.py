# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external import (
    MissingArgumentError,
    ResourceNotFound,
    ResourceUnavailable,
    ServiceUnavailable
)
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib import external_common
from socorro.webapi.webapiService import MiddlewareWebServiceBase

from configman import RequiredConfig, Namespace


class CrashDataBase(MiddlewareWebServiceBase):

    """
    Common implementation of the crash data service for all crashstorage
    schemes.  Any external service that wants to implement a CrashData service
    may subclass from this service.  All they'd have to do is implement the
    'get_storage' method to return an appropriate instance of their own
    crashstorage class.
    """

    uri = r'/crash_data/(.*)'

    def __init__(self, config):
        super(CrashDataBase, self).__init__(config)
        #self.config = kwargs['config']
        #self.all_services = kwargs['all_services']

    def get_storage(self):
        try:
            return self.config.crashstorage_class(
                self.config
            )
        except AttributeError, x:
            raise NotImplementedError(
                'derived classes are required to have attribute %s' % x
            )

    def get(self, **kwargs):
        """Return JSON data of a crash report, given its uuid. """

        filters = [
            ('uuid', None, 'str'),
            ('datatype', None, 'str')
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
                return (get(params.uuid), 'application/octet-stream')
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
                # get the Priorityjob service from configman
                services = self.config.services
                try:
                    priorityjob_class = services.Priorityjobs.cls
                except (KeyError, AttributeError):
                    raise ServiceUnavailable('Priorityjobs')
                priority_job_service = priorityjob_class(
                    config=services.Priorityjobs
                )
                priority_job_service.post(uuid=params.uuid)
                raise ResourceUnavailable(params.uuid)
            raise ResourceNotFound(params.uuid)
