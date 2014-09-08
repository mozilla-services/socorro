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
            def _do_run(klass):
                return 17

        eq_(SomeOtherApp._do_run(), 17)
        x = SomeOtherApp.run()
        eq_(x, 17)

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


#==============================================================================
class TestSocorroWelcomApp(TestCase):

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

