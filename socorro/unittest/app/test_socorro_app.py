import logging

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
)
from socorro.unittest.testbase import TestCase


class TestSocorroApp(TestCase):

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
        self.config.metrics.increment('increment_key')
        self.config.metrics.gauge('gauge_key', value=10)
        self.config.metrics.timing('timing_key', value=100)
        self.config.metrics.histogram('histogram_key', value=1000)


class TestSocorroAppMetrics:
    def test_logging_metrics(self, caplog):
        """Verify LoggingMetrics work"""
        caplog.set_level(logging.INFO)

        AppWithMetrics.run(values_source_list=[configman_keys({})])

        assert 'increment: increment_key=1 tags=[]' in caplog.text
        assert 'gauge: gauge_key=10 tags=[]' in caplog.text
        assert 'timing: timing_key=100 tags=[]' in caplog.text
        assert 'histogram: histogram_key=1000 tags=[]' in caplog.text

    def test_statsd_metrics(self, caplog):
        caplog.set_level(logging.INFO)

        with mock.patch('datadog.dogstatsd.statsd') as mock_statsd:
            vsl = configman_keys({
                'metricscfg.statsd_host': 'localhost',
                'metricscfg.statsd_port': '8125',
            })
            AppWithMetrics.run(values_source_list=[vsl])

            # Verify these didn't get logged
            assert 'increment: increment_key' not in caplog.text
            assert 'gauge: gauge_key' not in caplog.text
            assert 'timing: timing_key' not in caplog.text
            assert 'histogram: histogram_key' not in caplog.text

            # Verify they did get called on mock_statsd. Do this by converting the mock_calls call
            # objects to strings so they're easy to verify.
            mock_calls = [str(call) for call in mock_statsd.mock_calls]
            assert 'call.increment(\'increment_key\')' in mock_calls
            assert 'call.gauge(\'gauge_key\', value=10)' in mock_calls
            assert 'call.timing(\'timing_key\', value=100)' in mock_calls
            assert 'call.histogram(\'histogram_key\', value=1000)' in mock_calls
