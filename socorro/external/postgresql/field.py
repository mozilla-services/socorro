# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging

from socorro.external import MissingArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common


logger = logging.getLogger('webapi')


class Field(PostgreSQLBase):
    '''Implement the /field service with PostgreSQL. '''

    def get(self, **kwargs):
        '''Return data about a field from its name. '''
        filters = [
            ('name', None, 'str'),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.name:
            raise MissingArgumentError("name")

        sql = '''/* socorro.external.postgresql.field.Field.get */
            SELECT
                raw_field,
                transforms,
                product
            FROM data_dictionary
            WHERE raw_field=%(name)s
        '''

        error_message = 'Failed to retrieve field data from PostgreSQL'
        results = self.query(sql, params, error_message=error_message)

        field_data = {
            'name': None,
            'transforms': None,
            'product': None
        }

        if not results:
            return field_data

        field_data = dict(zip(('name', 'transforms', 'product'), results[0]))
        field_data['transforms'] = json.loads(field_data['transforms'])

        return field_data
