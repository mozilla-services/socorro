# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external import MissingOrBadArgumentError, ResourceNotFound, \
                             ResourceUnavailable
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.external.postgresql import priorityjobs
from socorro.lib import external_common

from . import crashstorage
from hbase_client import OoidNotFoundException

logger = logging.getLogger("webapi")


class CrashData(object):

    """
    Implement the /crash_data service with HBase.
    """

    def __init__(self, *args, **kwargs):
        super(CrashData, self).__init__()
        self.config = kwargs["config"]

    def get(self, **kwargs):
        """Return JSON data of a crash report, given its uuid. """
        filters = [
            ("uuid", None, "str"),
            ("datatype", None, "str")
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingOrBadArgumentError(
                        "Mandatory parameter 'uuid' is missing or empty")

        if not params.datatype:
            raise MissingOrBadArgumentError(
                        "Mandatory parameter 'datatype' is missing or empty")

        if hasattr(self.config, 'hbase'):
            config = self.config.hbase
            store = crashstorage.HBaseCrashStorage(config)

            datatype_method_mapping = {
                "raw": "get_raw_dump",
                "meta": "get_raw_crash",
                "processed": "get_processed"
            }

        else:
            # old middleware
            config = self.config
            import socorro.storage.crashstorage as cs
            store = cs.CrashStoragePool(
                config,
                storageClass=config.hbaseStorageClass
            ).crashStorage()

            datatype_method_mapping = {
                "raw": "get_raw_dump",
                "meta": "get_meta",
                "processed": "get_processed"
            }

        get = store.__getattribute__(datatype_method_mapping[params.datatype])
        try:
            if params.datatype == 'raw':
                return (get(params.uuid), 'application/octet-stream')
            else:
                return get(params.uuid)
        except (CrashIDNotFound, OoidNotFoundException):
            if params.datatype == 'processed':
                self.get(datatype='raw', uuid=params.uuid)
                j = priorityjobs.Priorityjobs(config=self.config)
                j.create(uuid=params.uuid)
                raise ResourceUnavailable(params.uuid)
            raise ResourceNotFound(params.uuid)
