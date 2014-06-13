# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import os

from collections import Sequence

from configman import ConfigurationManager, Namespace, environment
from socorro.lib.util import SilentFakeLogger

from socorro.external.elasticsearch import crashstorage
from socorro.middleware.middleware_app import MiddlewareApp
from socorro.unittest.middleware.setup_configman import (
    get_standard_config_manager
)
from socorro.unittest.testbase import TestCase


#==============================================================================
class ElasticSearchTestCase(TestCase):
    """Base class for Elastic Search related unit tests. """

    #--------------------------------------------------------------------------
    @staticmethod
    def get_standard_config_manager(
        more_definitions=None,
        service_classes=None,
        overrides=None,
    ):
        return get_standard_config_manager(
            more_definitions=more_definitions,
            service_classes=service_classes,
            overrides=overrides,
        )