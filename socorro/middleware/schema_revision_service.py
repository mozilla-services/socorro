# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class SchemaRevision(DataAPIService):
    """Provide current schema version at /schema_revision with PostgreSQL. """

    service_name = "schema_revision"
    uri = "/schema_revision/(.*)"

    def __init__(self, config):
        super(SchemaRevision, self).__init__(config)
        logger.debug('SchemaRevision service __init__')

    def get(self, *args):
        """Called when a get HTTP request is executed to /schema_revision """
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.ServerStatus(config=self.context)
        return impl.get(**params)
