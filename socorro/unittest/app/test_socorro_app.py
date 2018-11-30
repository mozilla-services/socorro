from configman import (
    Namespace,
    command_line,
    ConfigFileFutureProxy,
)
from configman.dotdict import DotDict, configman_keys
import mock
import pytest

from socorro.app.socorro_app import (
    App,
    SocorroApp,
    setup_logger,
)


class TestSocorroApp(object):
    def test_instantiation(self):
        config = DotDict()
        sa = SocorroApp(config)

        with pytest.raises(NotImplementedError):
            sa.main()
        with pytest.raises(NotImplementedError):
            sa._do_run()

    def test_run(self):
        class SomeOtherApp(SocorroApp):
            @classmethod
            def _do_run(klass, config_path=None, values_source_list=None):
                klass.config_path = config_path
                return 17

        assert SomeOtherApp._do_run() == 17
        assert SomeOtherApp.config_path is None
        x = SomeOtherApp.run()
        assert x == 17

    def test_run_with_alternate_config_path(self):
        class SomeOtherApp(SocorroApp):
            @classmethod
            def _do_run(klass, config_path=None, values_source_list=None):
                klass.values_source_list = values_source_list
                klass.config_path = config_path
                return 17

        assert SomeOtherApp._do_run('my/path') == 17
        assert SomeOtherApp.config_path == 'my/path'
        x = SomeOtherApp.run('my/other/path')
        assert x == 17
        assert SomeOtherApp.config_path == 'my/other/path'

    def test_run_with_alternate_values_source_list(self):
        class SomeOtherApp(SocorroApp):
            @classmethod
            def _do_run(klass, config_path=None, values_source_list=None):
                klass.values_source_list = values_source_list
                klass.config_path = config_path
                return 17

        assert SomeOtherApp._do_run('my/path', [{}, {}]) == 17
        assert SomeOtherApp.config_path == 'my/path'
        assert SomeOtherApp.values_source_list == [{}, {}]
        x = SomeOtherApp.run('my/other/path', [])
        assert x == 17
        assert SomeOtherApp.config_path == 'my/other/path'
        assert SomeOtherApp.values_source_list == []

    def test_do_run(self):
        with mock.patch('socorro.app.socorro_app.ConfigurationManager') as cm:
            cm.return_value.context.return_value = mock.MagicMock()
            with mock.patch('socorro.app.socorro_app.signal'):
                class SomeOtherApp(SocorroApp):
                    app_name = 'SomeOtherApp'
                    app_verision = '1.2.3'
                    app_description = 'a silly app'

                    def main(self):
                        expected = cm.return_value.context.return_value.__enter__.return_value
                        assert self.config is expected
                        return 17

                result = SomeOtherApp.run()
                args = cm.call_args_list
                args, kwargs = args[0]
                assert isinstance(args[0], Namespace)
                assert isinstance(kwargs['values_source_list'], list)
                assert kwargs['app_name'] == SomeOtherApp.app_name
                assert kwargs['app_version'] == SomeOtherApp.app_version
                assert kwargs['app_description'] == SomeOtherApp.app_description
                assert kwargs['config_pathname'] == './config'
                assert kwargs['values_source_list'][-1] == command_line
                assert isinstance(kwargs['values_source_list'][-2], DotDict)
                assert kwargs['values_source_list'][-3] is ConfigFileFutureProxy
                assert result == 17

    def test_do_run_with_alternate_class_path(self):
        with mock.patch('socorro.app.socorro_app.ConfigurationManager') as cm:
            cm.return_value.context.return_value = mock.MagicMock()
            with mock.patch('socorro.app.socorro_app.signal'):
                class SomeOtherApp(SocorroApp):
                    app_name = 'SomeOtherApp'
                    app_verision = '1.2.3'
                    app_description = 'a silly app'

                    def main(self):
                        expected = cm.return_value.context.return_value.__enter__.return_value
                        assert self.config is expected
                        return 17

                result = SomeOtherApp.run('my/other/path')

                args = cm.call_args_list
                args, kwargs = args[0]
                assert isinstance(args[0], Namespace)
                assert isinstance(kwargs['values_source_list'], list)
                assert kwargs['app_name'] == SomeOtherApp.app_name
                assert kwargs['app_version'] == SomeOtherApp.app_version
                assert kwargs['app_description'] == SomeOtherApp.app_description
                assert kwargs['config_pathname'] == 'my/other/path'
                assert kwargs['values_source_list'][-1] == command_line
                assert isinstance(kwargs['values_source_list'][-2], DotDict)
                assert kwargs['values_source_list'][-3] is ConfigFileFutureProxy
                assert result == 17

    def test_do_run_with_alternate_values_source_list(self):
        with mock.patch('socorro.app.socorro_app.ConfigurationManager') as cm:
            cm.return_value.context.return_value = mock.MagicMock()
            with mock.patch('socorro.app.socorro_app.signal'):
                class SomeOtherApp(SocorroApp):
                    app_name = 'SomeOtherApp'
                    app_verision = '1.2.3'
                    app_description = 'a silly app'

                    def main(self):
                        expected = cm.return_value.context.return_value.__enter__.return_value
                        assert self.config is expected
                        return 17

                result = SomeOtherApp.run(
                    config_path='my/other/path',
                    values_source_list=[{"a": 1}, {"b": 2}]
                )

                args = cm.call_args_list
                args, kwargs = args[0]
                assert isinstance(args[0], Namespace)
                assert kwargs['app_name'] == SomeOtherApp.app_name
                assert kwargs['app_version'] == SomeOtherApp.app_version
                assert kwargs['app_description'] == SomeOtherApp.app_description
                assert kwargs['config_pathname'] == 'my/other/path'
                assert isinstance(kwargs['values_source_list'], list)
                assert kwargs['values_source_list'][0] == {"a": 1}
                assert kwargs['values_source_list'][1] == {"b": 2}
                assert result == 17


class AppWithMetrics(App):
    def main(self):
        self.config.metrics.incr('increment_key')
        self.config.metrics.gauge('gauge_key', value=10)
        self.config.metrics.timing('timing_key', value=100)
        self.config.metrics.histogram('histogram_key', value=1000)


class TestSocorroAppMetrics(object):
    def test_metrics(self, metricsmock):
        """Verify LoggingMetrics work"""
        with metricsmock as mm:
            AppWithMetrics.run(values_source_list=[configman_keys({})])

            assert mm.has_record('incr', stat='increment_key', value=1)
            assert mm.has_record('gauge', stat='gauge_key', value=10)
            assert mm.has_record('timing', stat='timing_key', value=100)
            assert mm.has_record('histogram', stat='histogram_key', value=1000)


def test_setup_logger():
    """Verify setup_logger with level and root_level variations"""
    with mock.patch('socorro.app.socorro_app.logging.config.dictConfig') as dict_config_mock:
        # Defaults for level and root_level
        cfg = DotDict({
            'application': {
                'app_name': 'app'
            },
            'logging': {
                'level': 20,
                'root_level': 40,
                'format_string': 'foo'
            }
        })
        setup_logger(cfg, None, None)
        logging_config = dict_config_mock.call_args[0][0]

        assert 'root' not in logging_config
        assert 'propagate' not in logging_config['loggers']['socorro']
        assert 'propagate' not in logging_config['loggers']['app']

        # level == root_level
        cfg = DotDict({
            'application': {
                'app_name': 'app'
            },
            'logging': {
                'level': 20,
                'root_level': 20,
                'format_string': 'foo'
            }
        })
        setup_logger(cfg, None, None)
        logging_config = dict_config_mock.call_args[0][0]

        assert 'root' in logging_config
        assert logging_config['loggers']['socorro']['propagate'] == 0
        assert logging_config['loggers']['app']['propagate'] == 0

        # level < root_level
        cfg = DotDict({
            'application': {
                'app_name': 'app'
            },
            'logging': {
                'level': 20,
                'root_level': 10,
                'format_string': 'foo'
            }
        })
        setup_logger(cfg, None, None)
        logging_config = dict_config_mock.call_args[0][0]

        assert 'root' in logging_config
        assert logging_config['loggers']['socorro']['propagate'] == 0
        assert logging_config['loggers']['app']['propagate'] == 0
