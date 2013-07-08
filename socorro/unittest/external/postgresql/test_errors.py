# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.plugins.attrib import attr

from socorro.external.postgresql.errors import Errors
from socorro.lib import datetimeutil

from unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestErrors(PostgreSQLTestCase):
    """Test socorro.external.postgresql.errors.Errors class. """

    def setUp(self):
        super(IntegrationTestErrors, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        self.now = datetimeutil.utc_now()
        last_month = self.now - datetime.timedelta(weeks=4)
        uuid = "000aaf-98e0-4ece-a904-2573e2%s" % self.now.strftime("%y%m%d")

        # Insert valid data
        cursor.execute('''
            INSERT INTO bixie.crashes
            (
                crash_id,
                signature,
                error,
                product,
                processor_completed_datetime,
                success
            )
            VALUES
            (
                '01%(uuid)s',
                'i_can_haz_crash()',
                '{}',
                'ClockOClock',
                '%(now)s',
                TRUE
            ),
            (
                '02%(uuid)s',
                'i_can_haz_crash()',
                '{}',
                'ClockOClock',
                '%(now)s',
                TRUE
            ),
            (
                '03%(uuid)s',
                'heyIJustMetYou',
                '{}',
                'ClockOClock',
                '%(now)s',
                TRUE
            ),
            (
                '04%(uuid)s',
                'goGoGadgetCrash()',
                '{}',
                'EmailApp',
                '%(now)s',
                TRUE
            )
        ''' % {'now': self.now, 'uuid': uuid})

        # Insert vinalid data
        cursor.execute('''
            INSERT INTO bixie.crashes
            (
                crash_id,
                signature,
                error,
                product,
                processor_completed_datetime,
                success
            )
            VALUES
            (
                '11%(uuid)s',
                'i_can_haz_crash()',
                '{}',
                'ClockOClock',
                '%(last_month)s',
                TRUE
            ),
            (
                '12%(uuid)s',
                'i_can_haz_crash()',
                '{}',
                'ClockOClock',
                '%(now)s',
                NULL
            )
        ''' % {'now': self.now, 'last_month': last_month, 'uuid': uuid})

        self.connection.commit()

    def tearDown(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE bixie.crashes CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestErrors, self).tearDown()

    def test_get_signatures(self):
        api = Errors(config=self.config)

        # Test no parameter
        res = api.get_signatures()
        res_expected = {
            'hits': [
                {
                    'signature': 'i_can_haz_crash()',
                    'count': 2,
                },
                {
                    'signature': 'goGoGadgetCrash()',
                    'count': 1,
                },
                {
                    'signature': 'heyIJustMetYou',
                    'count': 1,
                },
            ],
            'total': 3
        }
        self.assertEqual(res, res_expected)

        # Test signature parameter
        res = api.get_signatures(signature='i_can_haz_crash()')
        res_expected = {
            'hits': [
                {
                    'signature': 'i_can_haz_crash()',
                    'count': 2,
                },
            ],
            'total': 1
        }
        self.assertEqual(res, res_expected)

        # Test search_mode parameter
        res = api.get_signatures(signature='et', search_mode='contains')
        res_expected = {
            'hits': [
                {
                    'signature': 'goGoGadgetCrash()',
                    'count': 1,
                },
                {
                    'signature': 'heyIJustMetYou',
                    'count': 1,
                },
            ],
            'total': 2
        }
        self.assertEqual(res, res_expected)

        # Test product parameter
        res = api.get_signatures(product='EmailApp')
        res_expected = {
            'hits': [
                {
                    'signature': 'goGoGadgetCrash()',
                    'count': 1,
                },
            ],
            'total': 1
        }
        self.assertEqual(res, res_expected)

        # Test date parameters
        res = api.get_signatures(
            start_date=self.now - datetime.timedelta(weeks=5),
            end_date=self.now - datetime.timedelta(weeks=3)
        )
        res_expected = {
            'hits': [
                {
                    'signature': 'i_can_haz_crash()',
                    'count': 1,
                },
            ],
            'total': 1
        }
        self.assertEqual(res, res_expected)
