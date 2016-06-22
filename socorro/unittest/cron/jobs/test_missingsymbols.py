import csv
import datetime
from cStringIO import StringIO

import mock
from crontabber.app import CronTabber

from socorro.unittest.cron.jobs.base import IntegrationTestBase
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


class TestMissingSymbolsCronApp(IntegrationTestBase):

    def setUp(self):
        super(TestMissingSymbolsCronApp, self).setUp()

        cursor = self.conn.cursor()
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

        self.conn.commit()

        self.mock_boto_class = mock.MagicMock()
        self.mock_bucket = mock.MagicMock()
        self.mock_key = mock.MagicMock()
        self.mock_boto_class()._get_or_create_bucket.return_value = (
            self.mock_bucket
        )
        self.mock_bucket.new_key.return_value = self.mock_key

    def tearDown(self):
        cursor = self.conn.cursor()

        # Ensure that the test partition entry and table no longer exist.
        statement = """
        TRUNCATE missing_symbols CASCADE
        """
        cursor.execute(statement)
        self.conn.commit()

        super(TestMissingSymbolsCronApp, self).tearDown()

    def _setup_config_manager(self, days_to_keep=None):
        super(TestMissingSymbolsCronApp, self)._setup_config_manager
        return get_config_manager_for_crontabber(
            jobs=(
                'socorro.cron.jobs.missingsymbols.MissingSymbolsCronApp|1d'
            ),
            overrides={
                'crontabber.class-MissingSymbolsCronApp'
                '.boto_class': self.mock_boto_class
            },
        )

    def test_basic_run(self):
        # We need to prepare to return a size for the new key
        self.mock_key.size = 123456789
        self.mock_key.generate_url.return_value = (
            'https://s3.example.com/latest.csv'
        )

        # Run the crontabber job to remove the test table.
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

        # Basic assertion test of stored procedure.
        information = self._load_structure()
        assert information['missing-symbols']
        assert not information['missing-symbols']['last_error']
        assert information['missing-symbols']['last_success']

        self.mock_boto_class()._connect.assert_called_with()
        self.mock_boto_class.close.assert_called_with()
        self.mock_bucket.new_key.assert_called_with('latest.csv')
        content = StringIO()
        writer = csv.writer(content)
        writer.writerow((
            'debug_file',
            'debug_id',
            'code_file',
            'code_id',
        ))
        writer.writerow((
            'nvwgf2um.pdb',
            '9D492B844FF34800B34320464AA1E7E41',
            'nvwgf2um.dll',
            '561D1D4Ff58000',
        ))
        self.mock_key.set_contents_from_string.assert_called_with(
            content.getvalue()
        )

        # this is becausse 123456789 bytes is 117.74 Mb
        tab.config.logger.info.assert_called_with(
            'Generated https://s3.example.com/latest.csv '
            '(123,456,789 bytes, 117.74 Mb)'
        )
