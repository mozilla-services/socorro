# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest import mock

from configman import Namespace, command_line, ConfigFileFutureProxy
from configman.dotdict import DotDict
import pytest

from socorro.app.socorro_app import App


class TestApp:
    def test_instantiation(self):
        config = DotDict()
        sa = App(config)

        with pytest.raises(NotImplementedError):
            sa.main()

    @mock.patch("socorro.app.socorro_app.setup_crash_reporting")
    @mock.patch("socorro.app.socorro_app.setup_logging")
    def test_run(self, setup_logging, setup_crash_reporting):
        with mock.patch("socorro.app.socorro_app.ConfigurationManager") as cm:
            cm.return_value.context.return_value = mock.MagicMock()

            class SomeOtherApp(App):
                app_name = "SomeOtherApp"
                app_verision = "1.2.3"
                app_description = "a silly app"

                def main(self):
                    expected = (
                        cm.return_value.context.return_value.__enter__.return_value
                    )
                    assert self.config is expected
                    return 17

            result = SomeOtherApp.run()
            args = cm.call_args_list
            args, kwargs = args[0]
            assert isinstance(args[0], Namespace)
            assert isinstance(kwargs["values_source_list"], list)
            assert kwargs["app_name"] == SomeOtherApp.app_name
            assert kwargs["app_version"] == SomeOtherApp.app_version
            assert kwargs["app_description"] == SomeOtherApp.app_description
            assert kwargs["config_pathname"] == "./config"
            assert kwargs["values_source_list"][-1] == command_line
            assert isinstance(kwargs["values_source_list"][-2], DotDict)
            assert kwargs["values_source_list"][-3] is ConfigFileFutureProxy
            assert result == 17

    @mock.patch("socorro.app.socorro_app.setup_logging")
    def test_run_with_alternate_config_path(self, setup_logging):
        class SomeOtherApp(App):
            @classmethod
            def run(klass, config_path=None, values_source_list=None):
                klass.values_source_list = values_source_list
                klass.config_path = config_path
                return 17

        assert SomeOtherApp.run("my/path") == 17
        assert SomeOtherApp.config_path == "my/path"
        x = SomeOtherApp.run("my/other/path")
        assert x == 17
        assert SomeOtherApp.config_path == "my/other/path"

    @mock.patch("socorro.app.socorro_app.setup_logging")
    def test_run_with_alternate_values_source_list(self, setup_logging):
        class SomeOtherApp(App):
            @classmethod
            def run(klass, config_path=None, values_source_list=None):
                klass.values_source_list = values_source_list
                klass.config_path = config_path
                return 17

        assert SomeOtherApp.run("my/path", [{}, {}]) == 17
        assert SomeOtherApp.config_path == "my/path"
        assert SomeOtherApp.values_source_list == [{}, {}]
        x = SomeOtherApp.run("my/other/path", [])
        assert x == 17
        assert SomeOtherApp.config_path == "my/other/path"
        assert SomeOtherApp.values_source_list == []

    @mock.patch("socorro.app.socorro_app.setup_crash_reporting")
    @mock.patch("socorro.app.socorro_app.setup_logging")
    def test_run_with_alternate_class_path(self, setup_logging, setup_crash_reporting):
        with mock.patch("socorro.app.socorro_app.ConfigurationManager") as cm:
            cm.return_value.context.return_value = mock.MagicMock()

            class SomeOtherApp(App):
                app_name = "SomeOtherApp"
                app_verision = "1.2.3"
                app_description = "a silly app"

                def main(self):
                    expected = (
                        cm.return_value.context.return_value.__enter__.return_value
                    )
                    assert self.config is expected
                    return 17

            result = SomeOtherApp.run("my/other/path")

            args = cm.call_args_list
            args, kwargs = args[0]
            assert isinstance(args[0], Namespace)
            assert isinstance(kwargs["values_source_list"], list)
            assert kwargs["app_name"] == SomeOtherApp.app_name
            assert kwargs["app_version"] == SomeOtherApp.app_version
            assert kwargs["app_description"] == SomeOtherApp.app_description
            assert kwargs["config_pathname"] == "my/other/path"
            assert kwargs["values_source_list"][-1] == command_line
            assert isinstance(kwargs["values_source_list"][-2], DotDict)
            assert kwargs["values_source_list"][-3] is ConfigFileFutureProxy
            assert result == 17
