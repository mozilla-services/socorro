# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock

from nose.tools import ok_

from crontabber.app import CronTabber
from socorro.unittest.cron.jobs.base import IntegrationTestBase

from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)
from socorro.schemas import CRASH_REPORT_JSON_SCHEMA_AS_STRING


class TestUploadCrashReportJSONSchemaCronApp(IntegrationTestBase):

    def _setup_config_manager(self):
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.upload_crash_report_json_schema.'
                 'UploadCrashReportJSONSchemaCronApp|30d',
        )

    @mock.patch('boto.connect_s3')
    def test_run(self, connect_s3):

        key = mock.MagicMock()
        connect_s3().get_bucket().get_key.return_value = None
        connect_s3().get_bucket().new_key.return_value = key

        with self._setup_config_manager().context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            app_name = 'upload-crash-report-json-schema'
            ok_(information[app_name])
            ok_(not information[app_name]['last_error'])
            ok_(information[app_name]['last_success'])

        key.set_contents_from_string.assert_called_with(
            CRASH_REPORT_JSON_SCHEMA_AS_STRING
        )
