import mock
from nose.tools import eq_, ok_, assert_raises
from socorro.unittest.testbase import TestCase

from configman import (
    Namespace,
    command_line,
    ConfigFileFutureProxy,
)
from configman.dotdict import DotDict, configman_keys
import pytest

from socorro.app.socorro_app import (
    App,
    SocorroApp,
    main,
)
from socorro.app.for_application_defaults import ApplicationDefaultsProxy


class TestSocorroApp(TestCase):

    def test_instantiation(self):
        config = DotDict()
        sa = SocorroApp(config)

        eq_(sa.get_application_defaults(), {})
        assert_raises(NotImplementedError, sa.main)
        assert_raises(NotImplementedError, sa._do_run)

    def test_run(self):
        class SomeOtherApp(SocorroApp):
            @classmethod
            def _do_run(klass, config_path=None, values_source_list=None):
                klass.config_path = config_path
                return 17

        eq_(SomeOtherApp._do_run(), 17)
        ok_(SomeOtherApp.config_path is None)
        x = SomeOtherApp.run()
        eq_(x, 17)

    def test_run_with_alternate_config_path(self):
        class SomeOtherApp(SocorroApp):
            @classmethod
            def _do_run(klass, config_path=None, values_source_list=None):
                klass.values_source_list = values_source_list
                klass.config_path = config_path
                return 17

        eq_(SomeOtherApp._do_run('my/path'), 17)
        eq_(SomeOtherApp.config_path, 'my/path')
        x = SomeOtherApp.run('my/other/path')
        eq_(x, 17)
        eq_(SomeOtherApp.config_path, 'my/other/path')

    def test_run_with_alternate_values_source_list(self):
        class SomeOtherApp(SocorroApp):
            @classmethod
            def _do_run(klass, config_path=None, values_source_list=None):
                klass.values_source_list = values_source_list
                klass.config_path = config_path
                return 17

        eq_(SomeOtherApp._do_run('my/path', [{}, {}]), 17)
        eq_(SomeOtherApp.config_path, 'my/path')
        eq_(SomeOtherApp.values_source_list, [{}, {}])
        x = SomeOtherApp.run('my/other/path', [])
        eq_(x, 17)
        eq_(SomeOtherApp.config_path, 'my/other/path')
        eq_(SomeOtherApp.values_source_list, [])

    def test_do_run(self):
        config = DotDict()
        with mock.patch('socorro.app.socorro_app.ConfigurationManager') as cm:
            cm.return_value.context.return_value = mock.MagicMock()
            with mock.patch('socorro.app.socorro_app.signal') as s:
                class SomeOtherApp(SocorroApp):
                    app_name='SomeOtherApp'
                    app_verision='1.2.3'
                    app_description='a silly app'
                    def main(self):
                        ok_(
                            self.config
                            is cm.return_value.context.return_value.__enter__
                                 .return_value
                        )
                        return 17

                result = main(SomeOtherApp)
                args = cm.call_args_list
                args, kwargs = args[0]
                ok_(isinstance(args[0], Namespace))
                ok_(isinstance(kwargs['values_source_list'], list))
                eq_(kwargs['app_name'], SomeOtherApp.app_name)
                eq_(kwargs['app_version'], SomeOtherApp.app_version)
                eq_(kwargs['app_description'], SomeOtherApp.app_description)
                eq_(kwargs['config_pathname'], './config')
                ok_(kwargs['values_source_list'][-1], command_line)
                ok_(isinstance(kwargs['values_source_list'][-2], DotDict))
                ok_(kwargs['values_source_list'][-3] is ConfigFileFutureProxy)
                ok_(isinstance(
                    kwargs['values_source_list'][0],
                    ApplicationDefaultsProxy
                ))
                eq_(result, 17)

    def test_do_run_with_alternate_class_path(self):
        config = DotDict()
        with mock.patch('socorro.app.socorro_app.ConfigurationManager') as cm:
            cm.return_value.context.return_value = mock.MagicMock()
            with mock.patch('socorro.app.socorro_app.signal') as s:
                class SomeOtherApp(SocorroApp):
                    app_name='SomeOtherApp'
                    app_verision='1.2.3'
                    app_description='a silly app'
                    def main(self):
                        ok_(
                            self.config
                            is cm.return_value.context.return_value.__enter__
                                 .return_value
                        )
                        return 17

                result = main(SomeOtherApp, 'my/other/path')

                args = cm.call_args_list
                args, kwargs = args[0]
                ok_(isinstance(args[0], Namespace))
                ok_(isinstance(kwargs['values_source_list'], list))
                eq_(kwargs['app_name'], SomeOtherApp.app_name)
                eq_(kwargs['app_version'], SomeOtherApp.app_version)
                eq_(kwargs['app_description'], SomeOtherApp.app_description)
                eq_(kwargs['config_pathname'], 'my/other/path')
                ok_(kwargs['values_source_list'][-1], command_line)
                ok_(isinstance(kwargs['values_source_list'][-2], DotDict))
                ok_(kwargs['values_source_list'][-3] is ConfigFileFutureProxy)
                ok_(isinstance(
                    kwargs['values_source_list'][0],
                    ApplicationDefaultsProxy
                ))
                eq_(result, 17)

    def test_do_run_with_alternate_values_source_list(self):
        config = DotDict()
        with mock.patch('socorro.app.socorro_app.ConfigurationManager') as cm:
            cm.return_value.context.return_value = mock.MagicMock()
            with mock.patch('socorro.app.socorro_app.signal') as s:
                class SomeOtherApp(SocorroApp):
                    app_name='SomeOtherApp'
                    app_verision='1.2.3'
                    app_description='a silly app'
                    def main(self):
                        ok_(
                            self.config
                            is cm.return_value.context.return_value.__enter__
                                 .return_value
                        )
                        return 17

                result = main(
                    SomeOtherApp,
                    config_path='my/other/path',
                    values_source_list=[{"a": 1}, {"b": 2}]
                )

                args = cm.call_args_list
                args, kwargs = args[0]
                ok_(isinstance(args[0], Namespace))
                eq_(kwargs['app_name'], SomeOtherApp.app_name)
                eq_(kwargs['app_version'], SomeOtherApp.app_version)
                eq_(kwargs['app_description'], SomeOtherApp.app_description)
                eq_(kwargs['config_pathname'], 'my/other/path')
                ok_(isinstance(kwargs['values_source_list'], list))
                ok_(isinstance(
                    kwargs['values_source_list'][0],
                    ApplicationDefaultsProxy
                ))
                eq_(kwargs['values_source_list'][1], {"a": 1})
                eq_(kwargs['values_source_list'][2], {"b": 2})
                eq_(result, 17)


class AppWithMetrics(App):
    def main(self):
        self.config.metrics.increment('increment_key')
        self.config.metrics.gauge('gauge_key', value=10)
        self.config.metrics.timing('timing_key', value=100)
        self.config.metrics.histogram('histogram_key', value=1000)


@pytest.mark.usefixtures('caplog')
class TestSocorroAppMetrics(TestCase):
    @pytest.fixture(autouse=True)
    def setup_caplog(self, caplog):
        """Adds caplog pytext fixture as an instance attribute for log analysis"""
        self.caplog = caplog

    def test_logging_metrics(self):
        """Verify LoggingMetrics work"""
        AppWithMetrics.run(values_source_list=[configman_keys({})])

        assert 'increment: increment_key=1 tags=[]' in self.caplog.text
        assert 'gauge: gauge_key=10 tags=[]' in self.caplog.text
        assert 'timing: timing_key=100 tags=[]' in self.caplog.text
        assert 'histogram: histogram_key=1000 tags=[]' in self.caplog.text

    def test_statsd_metrics(self):
        with mock.patch('datadog.dogstatsd.statsd') as mock_statsd:
            vsl = configman_keys({
                'metricscfg.statsd_host': 'localhost',
                'metricscfg.statsd_port': '8125',
            })
            AppWithMetrics.run(values_source_list=[vsl])

            # Verify these didn't get logged
            assert 'increment: increment_key' not in self.caplog.text
            assert 'gauge: gauge_key' not in self.caplog.text
            assert 'timing: timing_key' not in self.caplog.text
            assert 'histogram: histogram_key' not in self.caplog.text

            # Verify they did get called on mock_statsd. Do this by converting the mock_calls call
            # objects to strings so they're easy to verify.
            mock_calls = [str(call) for call in mock_statsd.mock_calls]
            assert 'call.increment(\'increment_key\')' in mock_calls
            assert 'call.gauge(\'gauge_key\', value=10)' in mock_calls
            assert 'call.timing(\'timing_key\', value=100)' in mock_calls
            assert 'call.histogram(\'histogram_key\', value=1000)' in mock_calls
