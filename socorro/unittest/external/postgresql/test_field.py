# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr

from socorro.external import MissingArgumentError
from socorro.external.postgresql.field import Field
from .unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestField(PostgreSQLTestCase):
    '''Test socorro.external.postgresql.field.Field class. '''

    def setUp(self):
        super(IntegrationTestField, self).setUp()

        cursor = self.connection.cursor()

        cursor.execute('''
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
        ''')

        self.connection.commit()

    def tearDown(self):
        '''Clean up the database, delete tables and functions. '''
        cursor = self.connection.cursor()
        cursor.execute('''
            TRUNCATE data_dictionary CASCADE
        ''')
        self.connection.commit()
        super(IntegrationTestField, self).tearDown()

    def test_get(self):
        api = Field(config=self.config)

        # expect a result
        res = api.get(name='field1')
        res_expected = {
            'name': 'field1',
            'transforms': {},
            'product': 'WaterWolf'
        }

        self.assertEqual(res, res_expected)

        # expect a result
        res = api.get(name='field2')
        res_expected = {
            'name': 'field2',
            'transforms': {'processor': 'some notes'},
            'product': 'WaterWolf'
        }

        self.assertEqual(res, res_expected)

        # expect no result
        res = api.get(name='i-do-not-exist')
        res_expected = {
            'name': None,
            'transforms': None,
            'product': None
        }

        self.assertEqual(res, res_expected)

        # expect a failure
        self.assertRaises(MissingArgumentError, api.get)
