# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import types

from nose.tools import ok_, eq_

from socorro.external.postgresql.missing_symbols import MissingSymbols
from unittestbase import PostgreSQLTestCase


class IntegrationTestMissingSymbols(PostgreSQLTestCase):
    """Test socorro.external.postgresql.missing_symbols.MissingSymbols
    class."""

    def setUp(self):
        super(IntegrationTestMissingSymbols, self).setUp()

        cursor = self.connection.cursor()
        today = datetime.datetime.utcnow().date()
        yesterday = today - datetime.timedelta(days=1)

        cursor.execute("""
            INSERT INTO missing_symbols
            (date_processed, debug_file, debug_id, code_file, code_id)
            VALUES
            (
                %(today)s,
                'McBrwCtl.pdb',
                '133A2F3537E341A995D7C2BF8C3B2C663',
                '',
                ''
            ),
            (
                %(today)s,
                'msmpeg2vdec.pdb',
                '8515599DC90B4A01997BA2647DFE24941',
                'msmpeg2vdec.dll',
                '54134E292c4000'
            ),
            (
                %(today)s,
                '',
                '8515599DC90B4A01997BA2647DFE24941',
                'msmpeg2vdec.dll',
                '54134E292c4000'
            ),
            (
                %(today)s,
                'msmpeg2vdec.pdb',
                '',
                'msmpeg2vdec.dll',
                '54134E292c4000'
            ),
            (
                %(yesterday)s,
                'nvwgf2um.pdb',
                '9D492B844FF34800B34320464AA1E7E41',
                'nvwgf2um.dll',
                '561D1D4Ff58000'
            ),
            (
                %(yesterday)s,
                'nvwgf2um.pdb',
                '',
                'nvwgf2um.dll',
                '561D1D4Ff58000'
            ),
            (
                %(yesterday)s,
                '',
                '9D492B844FF34800B34320464AA1E7E41',
                'nvwgf2um.dll',
                '561D1D4Ff58000'
            )
        """, {'today': today, 'yesterday': yesterday})

        self.connection.commit()
        cursor.close()

    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE missing_symbols
            CASCADE
        """)
        self.connection.commit()
        cursor.close()
        super(IntegrationTestMissingSymbols, self).tearDown()

    def test_iter(self):
        implementation = MissingSymbols(config=self.config)
        today = datetime.datetime.utcnow().date()
        res = implementation.iter(date=today)
        ok_(isinstance(res, types.GeneratorType))

        rows = sorted(list(res))  # run the generator into a list
        expected = sorted([
            {
                'debug_file': 'McBrwCtl.pdb',
                'debug_id': '133A2F3537E341A995D7C2BF8C3B2C663',
                'code_file': '',
                'code_id': '',
            },
            {
                'debug_file': 'msmpeg2vdec.pdb',
                'debug_id': '8515599DC90B4A01997BA2647DFE24941',
                'code_file': 'msmpeg2vdec.dll',
                'code_id': '54134E292c4000',
            },
        ])
        eq_(rows, expected)
