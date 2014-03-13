# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import tempfile
import shutil
import os
import unittest
import mock
from nose.tools import eq_
from configman import Namespace
from configman.config_file_future_proxy import ConfigFileFutureProxy
from socorro.app.generic_app import App, main


class MyApp(App):
    app_name = 'myapp'
    app_version = '1.0'
    app_description = 'bla bla'

    required_config = Namespace()
    required_config.add_option(
        name='color_or_colour',
        default='colour',
        doc='How do you spell it?',
    )

    def main(self):
        self.config.logger.error(self.config.color_or_colour)


class ExitingApp(MyApp):
    app_name = 'exitingapp'

    required_config = Namespace()
    required_config.add_option(
        name='exit_code',
        default='0',
        doc='How do you want it to exit',
    )

    def main(self):
        return self.config.exit_code


class TestGenericAppConfigPathLoading(unittest.TestCase):
    """
    Test that it's possible to override the default directory from where
    generic_app tries to read default settings from.

    This is depending on there being an environment variable called
    DEFAULT_SOCORRO_CONFIG_PATH which must exist.
    """

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    @mock.patch('socorro.app.generic_app.logging')
    def test_overriding_config_path(self, logging):
        vsl = (ConfigFileFutureProxy,)
        exit_code = main(MyApp, values_source_list=vsl)
        eq_(exit_code, 0)

        os.environ['DEFAULT_SOCORRO_CONFIG_PATH'] = '/foo/bar'
        self.assertRaises(IOError, main, (MyApp,), values_source_list=vsl)

        os.environ['DEFAULT_SOCORRO_CONFIG_PATH'] = self.tempdir
        exit_code = main(MyApp, values_source_list=vsl)
        eq_(exit_code, 0)

        logging.getLogger().error.assert_called_with(' - MainThread - colour')

        _ini_file = os.path.join(self.tempdir, 'myapp.ini')
        with open(_ini_file, 'w') as f:
            f.write('color_or_colour=color\n')

        exit_code = main(MyApp, values_source_list=vsl)
        eq_(exit_code, 0)

        logging.getLogger().error.assert_called_with(' - MainThread - color')

    @mock.patch('socorro.app.generic_app.logging')
    def test_exit_codes(self, logging):
        vsl = (ConfigFileFutureProxy, {'exit_code': 123})
        exit_code = main(ExitingApp, values_source_list=vsl)
        eq_(exit_code, 123)

        vsl = (ConfigFileFutureProxy, {'exit_code': 0})
        exit_code = main(ExitingApp, values_source_list=vsl)
        eq_(exit_code, 0)

        vsl = (ConfigFileFutureProxy, {'exit_code': None})
        exit_code = main(ExitingApp, values_source_list=vsl)
        eq_(exit_code, 0)
