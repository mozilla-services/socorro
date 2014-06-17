# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)

from crontabber.tests import base

class IntegrationTestBase(base.IntegrationTestCaseBase):

    def get_standard_config(self):
        """this method overrides the crontabber version of the same name.
        It is not used by Socorro clients directly, but the base crontabber
        class uses this method during setup.  By overriding the implementation
        here, we get a default Socorro configuration file with many of the
        standard Socorro defaults already in place: logging, executors, etc.
        This allows the bootstraping of the integration tests to participate
        fully with the environment variables, commandline arguments, and
        configurations files that the Socorro installation/test system of
        Makefiles and shell scripts offers"""
        config = get_config_manager_for_crontabber().get_config()
        return config


