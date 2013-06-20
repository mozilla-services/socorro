# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import copy
from mock import (Mock, patch, call)

from configman.dotdict import DotDict

from socorro.processor.bixie_processor import (
    BixieProcessor,
    signature_action
)


def setup_config_with_mocks():
    config = DotDict()
    config.processor_name = 'dwight'
    config.database_class = Mock()
    config.transaction_executor_class = Mock()
    config.statistics = DotDict()
    config.statistics.stats_class = Mock()
    config.logger = Mock()
    return config


canonical_raw_crash = {
    "submitted_timestamp": "2013-05-04T15:10:00",
    "base_uri": "BASE_URI",
    "project_id": "PROJECT_ID",
    "sentry_version": u"2.0",
    "crash_id": "c796b8db-f5b4-40b1-8849-bb7682130504",
    "sentry_client": u"raven-js/1.0.7",
    "sentry_key": "public",
    "sentry_data": {
        u"sentry.interfaces.Exception": {
            u"type": u"ReferenceError",
            u"value": u"Can't find variable: doSomething"
        },
        "culprit": u"file:///Users/lonnen/repos/hrafnsmal/pages/index.html",
        u"message": u"Can't find variable: doSomething",
        u"project": 0,
        u"platform": u"javascript",
        u"sentry.interfaces.Http": {
            u"url": u"file:///Users/lonnen/repos/hrafnsmal/pages/index.html",
            u"headers": {
                u"User-Agent": u"Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/534.34 (KHTML, like Gecko) PhantomJS/1.9.0 Safari/534.34"
            }
        },
        u"logger": u"javascript",
        u"sentry.interfaces.Stacktrace": {
            u"frames": [
                {
                    u"function": u"?",
                    u"in_app": True,
                    u"lineno": 3,
                    u"colno": None,
                    u"filename": u"file:///Users/lonnen/repos/hrafnsmal/pages/hrafnsmal.js"
                }
            ]
        }
    }
}

class TestBixieProcessor(unittest.TestCase):

    def test_init(self):
        config = setup_config_with_mocks()
        class MyBixieProcessor(BixieProcessor):
            def _load_transform_rules(self):
                self.rule_system.load_rules([])
        bp = MyBixieProcessor(config)
        self.assertFalse(bp.quit_check())
        config.database_class.assert_called_once_with(config)
        config.transaction_executor_class.assert_called_once_with(
            config,
            bp.database,
            bp.quit_check
        )
        self.assertEqual(bp.rule_system.rules, [])
        config.statistics.stats_class.assert_called_once_with(
            config.statistics,
            config.processor_name
        )
        bp._statistics.incr.assert_called_once_with('restarts')

    def test_reject_raw_crash(self):
        config = setup_config_with_mocks()
        class MyBixieProcessor(BixieProcessor):
            def _load_transform_rules(self):
                self.rule_system.load_rules([])
        with patch('socorro.processor.bixie_processor.utc_now') as mocked_now:
            mocked_now.return_value = 17
            bp = MyBixieProcessor(config)
            bp.reject_raw_crash(
                'c796b8db-f5b4-40b1-8849-bb7682130504',
                'because I said so'
            )
            expected_info_log_calls = [
                call(
                    'starting job: %s',
                    'c796b8db-f5b4-40b1-8849-bb7682130504',
                ),
                call(
                    'finishing %s job: %s',
                    'failed',
                    'c796b8db-f5b4-40b1-8849-bb7682130504',
                )
            ]
            self.assertEqual(
                config.logger.info.call_args_list,
                expected_info_log_calls
            )
            config.logger.warning.assert_called_once_with(
                '%s rejected: %s',
                'c796b8db-f5b4-40b1-8849-bb7682130504',
                'because I said so'
            )

    def test_convert_raw_crash_to_processed_crash(self):
        config = setup_config_with_mocks()
        class MyBixieProcessor(BixieProcessor):
            def _load_transform_rules(self):
                self.rule_system.load_rules([])
        with patch('socorro.processor.bixie_processor.utc_now') as mocked_now:
            mocked_now.return_value = 17
            mocked_quit_function = Mock()
            bp = MyBixieProcessor(config, mocked_quit_function)
            processed_crash = bp.convert_raw_crash_to_processed_crash(
                canonical_raw_crash,
                {}  # no binary attachments
            )

            bp._statistics.incr.called_once_with()
            mocked_quit_function.assert_called_once_with()
            self.assertEqual(processed_crash.processor.name, 'dwight')
            self.assertEqual(processed_crash.processor.notes, [])
            self.assertEqual(processed_crash.signature, '')
            self.assertEqual(
                processed_crash.processor.started_timestamp,
                17
            )
            self.assertEqual(
                processed_crash.processor.completed_timestamp,
                17
            )
            self.assertEqual(
                processed_crash.crash_id,
                "c796b8db-f5b4-40b1-8849-bb7682130504"
            )
            self.assertEqual(
                processed_crash.crash_id,
                "c796b8db-f5b4-40b1-8849-bb7682130504"
            )

    def test_signature_action(self):
        processed_crash = DotDict()
        signature_action(canonical_raw_crash, {}, processed_crash, None)
        self.assertEqual(
            processed_crash.signature,
            "file:///Users/lonnen/repos/hrafnsmal/pages/hrafnsmal.js:3 ?"
        )

        signature_action({}, {}, processed_crash, None)
        self.assertEqual(
            processed_crash.signature,
            "unknown file:? unknown fn"
        )

