# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose.tools import eq_, assert_raises

from socorro.external import MissingArgumentError
from socorro.external.postgresql.field_service import Field
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
)
from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestField(PostgreSQLTestCase):
    '''Test socorro.external.postgresql.field_service.Field class. '''

    #--------------------------------------------------------------------------
    def setUp(self):
        super(IntegrationTestField, self).setUp(Field)
        self.transaction(
            execute_no_results,
            '''
                INSERT INTO data_dictionary
                (raw_field, transforms, product)
                VALUES
                (
                    'field1',
                    '{}',
                    'WaterWolf'
                ),
                (
                    'field2',
                    '{"processor": "some notes"}',
                    'WaterWolf'
                );
            '''
        )

    #--------------------------------------------------------------------------
    def tearDown(self):
        '''Clean up the database, delete tables and functions. '''
        self.transaction(
            execute_no_results,
            ' TRUNCATE data_dictionary CASCADE'
        )
        super(IntegrationTestField, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        api = Field(config=self.config)

        # expect a result
        res = api.get(name='field1')
        res_expected = {
            'name': 'field1',
            'transforms': {},
            'product': 'WaterWolf'
        }

        eq_(res, res_expected)

        # expect a result
        res = api.get(name='field2')
        res_expected = {
            'name': 'field2',
            'transforms': {'processor': 'some notes'},
            'product': 'WaterWolf'
        }

        eq_(res, res_expected)

        # expect no result
        res = api.get(name='i-do-not-exist')
        res_expected = {
            'name': None,
            'transforms': None,
            'product': None
        }

        eq_(res, res_expected)

        # expect a failure
        assert_raises(MissingArgumentError, api.get)
