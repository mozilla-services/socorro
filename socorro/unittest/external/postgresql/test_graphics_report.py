# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.plugins.attrib import attr
from nose.tools import eq_, ok_

from socorro.external.postgresql.graphics_report import GraphicsReport

from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestGraphicsReport(PostgreSQLTestCase):
    """Test socorro.external.postgresql.graphics_report.GraphicsReport
     class. """

    @classmethod
    def setUpClass(cls):
        """ Populate product_info table with fake data """
        super(IntegrationTestGraphicsReport, cls).setUpClass()

        cursor = cls.connection.cursor()

        cursor.execute("""
            INSERT INTO products
            (product_name, sort, rapid_release_version, release_name)
            VALUES
            (
                'Firefox',
                1,
                '8.0',
                'firefox'
            ),
            (
                'Fennec',
                3,
                '11.0',
                'mobile'
            ),
            (
                'Thunderbird',
                2,
                '10.0',
                'thunderbird'
            );
        """)
        today = datetime.datetime.utcnow().date()
        cursor.execute("""
            INSERT INTO reports
            (id, signature, date_processed, uuid, product,
             url, email, success, addons_checked)
            VALUES
            (
                1,
                'signature',
                %s,
                '1',
                'Firefox',
                'http://mywebsite.com',
                'test@something.com',
                TRUE,
                TRUE
            ),
            (
                2,
                'my signature',
                %s,
                '2',
                'Firefox',
                'http://myotherwebsite.com',
                'admin@example.com',
                NULL,
                FALSE
            );
        """, (today, today))

        cls.connection.commit()

    #--------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):
        """ Cleanup the database, delete tables and functions """
        cursor = cls.connection.cursor()
        cursor.execute("""
            TRUNCATE products, reports
            CASCADE
        """)
        cls.connection.commit()
        super(IntegrationTestGraphicsReport, cls).tearDownClass()

    #--------------------------------------------------------------------------
    def test_get(self):
        api = GraphicsReport(config=self.config)
        res = api.get(product='Firefox')
        ok_(res['header'])
        eq_(res['header'][0], 'signature')
        eq_(res['header'][-1], 'productid')
        assert res['hits']
        ok_(isinstance(res['hits'], list))
        signatures = [x[0] for x in res['hits']]
        eq_(signatures, ['my signature', 'signature'])
