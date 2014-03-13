# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from nose.plugins.attrib import attr
from nose.tools import eq_, assert_raises

from socorro.external import MissingArgumentError
from socorro.external.postgresql.graphics_devices import GraphicsDevices

from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestGraphicsDevices(PostgreSQLTestCase):

    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE graphics_device
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestGraphicsDevices, self).tearDown()

    def _insert(self, vendor_hex, adapter_hex,
                vendor_name='', adapter_name=''):
        assert vendor_hex and adapter_hex
        assert vendor_name or adapter_name
        sql = """
        INSERT INTO graphics_device (
            vendor_hex,
            adapter_hex,
            vendor_name,
            adapter_name
        ) VALUES (%s, %s, %s, %s)
        """
        cursor = self.connection.cursor()
        params = (vendor_hex, adapter_hex, vendor_name, adapter_name)
        cursor.execute(sql, params)
        self.connection.commit()

    def test_get(self):
        """returning rows by matching vendor_hex and adapter_hex"""
        api = GraphicsDevices(config=self.config)

        params = {
            'vendor_hex': '0x1002',
            'adapter_hex': '0x0166',
        }
        res = api.get(**params)
        res_expected = {
            'hits': [],
            'total': 0
        }
        eq_(res, res_expected)

        # insert something similar
        self._insert(
            '0x1002', '0x0166',
            vendor_name='Logitech Inc.',
            adapter_name='Unknown Webcam Pro 9000'
        )
        self._insert(
            '0x1002', '0xc064',
            vendor_name='Logitech Inc.',
            adapter_name='k251d DELL 6-Button mouse'
        )
        self._insert(
            '0x1222', '0x0166',
            vendor_name='Chicony Electronics Co.',
            adapter_name='Unknown Webcam Pro 9000'
        )

        # now we should get something
        res = api.get(**params)
        res_expected = {
            'hits': [{
                'vendor_hex': '0x1002',
                'adapter_hex': '0x0166',
                'vendor_name': 'Logitech Inc.',
                'adapter_name': 'Unknown Webcam Pro 9000'
            }],
            'total': 1
        }
        eq_(res, res_expected)

    def test_get_missing_arguments(self):
        """on .get() the adapter_hex and the vendor_hex is mandatory"""
        api = GraphicsDevices(config=self.config)
        assert_raises(
            MissingArgumentError,
            api.get
        )
        assert_raises(
            MissingArgumentError,
            api.get,
            adapter_hex='something'
        )
        assert_raises(
            MissingArgumentError,
            api.get,
            vendor_hex='something'
        )
        assert_raises(
            MissingArgumentError,
            api.get,
            vendor_hex='something',
            adapter_hex=''  # empty!
        )
        assert_raises(
            MissingArgumentError,
            api.get,
            vendor_hex='',  # empty!
            adapter_hex='something'
        )

    def test_post_insert(self):
        payload = [
            {
                'vendor_hex': '0x1002',
                'adapter_hex': '0x0166',
                'vendor_name': 'Logitech Inc.',
                'adapter_name': 'Unknown Webcam Pro 9000'
            },
        ]

        api = GraphicsDevices(config=self.config)
        res = api.post(data=json.dumps(payload))
        eq_(res, True)

        cursor = self.connection.cursor()
        cursor.execute("""
            select vendor_hex, adapter_hex, vendor_name, adapter_name
            from graphics_device
            order by vendor_hex, adapter_hex
        """)
        expect = []
        keys = 'vendor_hex', 'adapter_hex', 'vendor_name', 'adapter_name'
        for row in cursor.fetchall():
            expect.append(dict(zip(keys, row)))

        eq_(expect, payload)

    def test_post_update(self):
        self._insert(
            '0x1002', '0x0166',
            vendor_name='Logitech Inc.',
            adapter_name='Unknown Webcam Pro 9000'
        )

        payload = [
            {
                'vendor_hex': '0x1002',
                'adapter_hex': '0x0166',
                'vendor_name': 'Logitech Inc.',
                'adapter_name': 'Known Webcam Pro 10000'  # the change
            }
        ]

        api = GraphicsDevices(config=self.config)
        res = api.post(data=json.dumps(payload))
        eq_(res, True)

        cursor = self.connection.cursor()
        cursor.execute("""
            select vendor_hex, adapter_hex, vendor_name, adapter_name
            from graphics_device
            order by vendor_hex, adapter_hex
        """)
        expect = []
        keys = 'vendor_hex', 'adapter_hex', 'vendor_name', 'adapter_name'
        for row in cursor.fetchall():
            expect.append(dict(zip(keys, row)))

        eq_(expect, payload)

    def test_post_upsert(self):
        """on .post() every item you send in the payload causes an upsert"""
        # first, insert something that we're going have to do nothing with
        # or do an "upsert"
        self._insert(
            '0x1002', '0x0166',
            vendor_name='Logitech Inc.',
            adapter_name='Unknown Webcam Pro 9000'
        )
        self._insert(
            '0x1222', '0x0166',
            vendor_name='Chicony Electronics Co.',
            adapter_name='Unknown Webcam Pro 9000'
        )

        # note, this is conveniently sorted by
        # vendor_hex followed by adapter_hex
        payload = [
            {
                'vendor_hex': '0x1002',
                'adapter_hex': '0x0166',
                'vendor_name': 'Logitech Inc.',
                'adapter_name': 'Unknown Webcam Pro 9000'
            },
            {
                'vendor_hex': '0x1222',
                'adapter_hex': '0x0166',
                'vendor_name': 'Chicony Electronics Co.',
                'adapter_name': 'Something else'
            },
            {
                'vendor_hex': '0x1333',
                'adapter_hex': '0x0177',
                'vendor_name': 'IBM',
                'adapter_name': ''
            },
        ]

        api = GraphicsDevices(config=self.config)
        res = api.post(data=json.dumps(payload))
        eq_(res, True)

        cursor = self.connection.cursor()
        cursor.execute("""
            select vendor_hex, adapter_hex, vendor_name, adapter_name
            from graphics_device
            order by vendor_hex, adapter_hex
        """)
        expect = []
        keys = 'vendor_hex', 'adapter_hex', 'vendor_name', 'adapter_name'
        for row in cursor.fetchall():
            expect.append(dict(zip(keys, row)))

        eq_(expect, payload)

    def test_post_fail(self):
        payload = [
            {
                'rubbish': 'Crap'
            },
        ]
        api = GraphicsDevices(config=self.config)
        res = api.post(data=json.dumps(payload))
        eq_(res, False)
