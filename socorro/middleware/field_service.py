# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger('webapi')


class Field(DataAPIService):
    '''Return data about a field from its name. '''

    service_name = 'field'
    uri = '/field/(.*)'

    def __init__(self, config):
        super(Field, self).__init__(config)
        logger.debug('Field service __init__')

    def get(self, *args):
        '''Called when a get HTTP request is executed to /field. '''
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.Field(config=self.context)
        return impl.get(**params)
