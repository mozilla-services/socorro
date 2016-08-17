# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace, ConfigurationManager

from socorro.unittest.testbase import TestCase
from socorro.external.metrics_base import MetricsBase


class TestMetricsBase(TestCase):
    def test_init(self):
        # This is a really basic test to make sure initialization works since
        # it can be used as a no-op class.
        required_config = Namespace()
        required_config.update(MetricsBase.required_config)

        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[],
            argv_source=[]
        )

        with config_manager.context() as config:
            # Does it initialize without errors?
            metrics = MetricsBase(config)

            # Does it run capture_stats without errors?
            data_items = {'foo': 5}
            metrics.capture_stats(data_items)
