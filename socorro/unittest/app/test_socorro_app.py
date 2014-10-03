import mock
from nose.tools import eq_, ok_, assert_raises
from socorro.unittest.testbase import TestCase
from socorro.processor.processor_app import ProcessorApp
from configman import (
    class_converter,
    Namespace,
    command_line,
    ConfigFileFutureProxy,
)
from configman.dotdict import DotDict

from socorro.app.socorro_app import (
    SocorroApp,
    SocorroWelcomeApp,
    main,
    klass_to_pypath,
)
from socorro.app.for_application_defaults import ApplicationDefaultsProxy

tag = ''

#==============================================================================
# used in tests below
class MyProcessor(ProcessorApp):
    def main(self):
        global tag
        tag = 'lars was here'
        return "I'm a dummy main"


#==============================================================================
class TestSocorroApp(TestCase):

    #--------------------------------------------------------------------------
    def test_instantiation(self):
        config = DotDict()
        sa = SocorroApp(config)

        eq_(sa.get_application_defaults(), {})
        assert_raises(NotImplementedError, sa.main)
        assert_raises(NotImplementedError, sa._do_run)

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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


    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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


    #--------------------------------------------------------------------------
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



#==============================================================================
class TestSocorroWelcomeApp(TestCase):

    #--------------------------------------------------------------------------
    def test_instantiation(self):
        config = DotDict()
        sa = SocorroWelcomeApp(config)
        eq_(sa.config, config)
        eq_(
            sa.required_config.application.default,
            None
        )

    #--------------------------------------------------------------------------
    def test_app_replacement(self):
        config = DotDict()
        config.application = MyProcessor

        with mock.patch(
            'socorro.app.socorro_app.command_line',
            new={}
        ) as mocked_command:
            sa = SocorroWelcomeApp(config)
            sa.main()
            eq_(tag, 'lars was here')


#--------------------------------------------------------------------------
def test_klass_to_pypath_various_modules():
    from socorro.processor.processor_app import ProcessorApp
    eq_(
        klass_to_pypath(ProcessorApp),
        'socorro.processor.processor_app.ProcessorApp'
    )


#--------------------------------------------------------------------------
def test_klass_to_pypath_a_faked_out_main():

    # since we can't really get a class that reports its __module__ as
    # being '__main__', we have to fake it with mocks.

    fake_sys_modules = {
        '__main__': '/some/bogus/path/socoro/processor/processor_app.py',
    }
    fake_sys_path = [
        '', '/my/home/path', '/your/home/path', '/some/bogus/path',
        '/elsewhere/'
    ]

    MockedMainClass = mock.Mock()
    MockedMainClass.__module__ = '__main__'
    MockedMainClass.__name__ = 'ProcessorApp'

    with mock.patch(
        'socorro.app.socorro_app.sys.modules',
        new=fake_sys_modules
    ):
        with mock.patch(
            'socorro.app.socorro_app.sys.path',
            new=fake_sys_path
        ):
            eq_(
                klass_to_pypath(ProcessorApp),
                'socorro.processor.processor_app.ProcessorApp'
            )
