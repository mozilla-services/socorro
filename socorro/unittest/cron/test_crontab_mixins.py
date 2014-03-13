import unittest

import mock
from nose.tools import eq_, ok_

from configman import ConfigurationManager, Namespace
from configman.dotdict import DotDict

from socorro.cron.base import BaseCronApp
import socorro.cron.mixins as ctm

from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.database.transaction_executor import TransactionExecutor


class FakeResourceClass(object):
    pass


class TestCrontabMixins(unittest.TestCase):

    def test_as_backfill_cron_app_simple_success(self):
        @ctm.as_backfill_cron_app
        class Alpha(BaseCronApp):
            pass
        a = Alpha(mock.Mock(), mock.Mock())
        ok_(hasattr(a, 'main'))
        ok_(hasattr(Alpha, 'required_config'))

    def test_as_backfill_cron_app_main_overrides(self):
        @ctm.as_backfill_cron_app
        class Alpha(BaseCronApp):
            def main(self, function, once):
                yield 'yuck'
        config = DotDict()
        config.time = '00:01'
        config.frequency = '1m'
        a = Alpha(config, None)
        ok_(hasattr(a, 'main'))
        with mock.patch('socorro.cron.base.utc_now') as mocked_utc_now:
            mocked_utc_now.return_value = 'dwight'
            for i in a.main(lambda t: 18):
                eq_(i, 'dwight')

    def test_with_transactional_resource(self):
        @ctm.with_transactional_resource(
            'socorro.external.postgresql.connection_context.ConnectionContext',
            'database'
        )
        class Alpha(BaseCronApp):
            pass
        self.assertTrue
        ok_(hasattr(Alpha, "required_config"))
        alpha_required = Alpha.get_required_config()
        ok_(isinstance(alpha_required, Namespace))
        ok_('database' in alpha_required)
        ok_('database_class' in alpha_required.database)
        ok_(
            'database_transaction_executor_class' in alpha_required.database
        )
        cm = ConfigurationManager(
            definition_source=[Alpha.get_required_config(), ],
            values_source_list=[],
            argv_source=[],
        )
        config = cm.get_config()
        a = Alpha(config, mock.Mock())
        ok_(hasattr(a, 'database_connection'))
        ok_(isinstance(
            a.database_connection,
            ConnectionContext
        ))
        ok_(hasattr(a, 'database_transaction'))
        ok_(isinstance(
            a.database_transaction,
            TransactionExecutor
        ))

    def test_with_resource_connection_as_argument(self):
        @ctm.with_transactional_resource(
            'socorro.external.postgresql.connection_context.ConnectionContext',
            'database'
        )
        @ctm.with_resource_connection_as_argument('database')
        class Alpha(BaseCronApp):
            def __init__(self, config):
                self.config = config
        ok_(hasattr(Alpha, '_run_proxy'))

    def test_with_subprocess_mixin(self):
        @ctm.with_transactional_resource(
            'socorro.external.postgresql.connection_context.ConnectionContext',
            'database'
        )
        @ctm.with_single_transaction('database')
        @ctm.with_subprocess
        class Alpha(BaseCronApp):
            def __init__(self, config):
                self.config = config
        ok_(hasattr(Alpha, '_run_proxy'))
        ok_(hasattr(Alpha, 'run_process'))

    def test_with_postgres_transactions(self):
        @ctm.with_postgres_transactions()
        class Alpha(BaseCronApp):
            def __init__(self, config):
                self.config = config
        self.assertTrue
        ok_(hasattr(Alpha, "required_config"))
        alpha_required = Alpha.get_required_config()
        ok_(isinstance(alpha_required, Namespace))
        ok_('database' in alpha_required)
        ok_('database_class' in alpha_required.database)
        ok_(
            'database_transaction_executor_class' in alpha_required.database
        )

    def test_with_postgres_connection_as_argument(self):
        @ctm.with_postgres_transactions()
        @ctm.with_postgres_connection_as_argument()
        class Alpha(BaseCronApp):
            def __init__(self, config):
                self.config = config
        ok_(hasattr(Alpha, '_run_proxy'))
