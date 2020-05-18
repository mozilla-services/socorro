# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest import mock

from configman import ConfigurationManager
from configman.dotdict import DotDict

from socorro.processor.processor_pipeline import ProcessorPipeline
from socorro.processor.rules.general import CPUInfoRule, OSInfoRule
from socorro.processor.rules.base import Rule


class BadRule(Rule):
    def action(self, *args, **kwargs):
        raise KeyError("pii")


class TestProcessorPipeline:
    def get_config(self):
        cm = ConfigurationManager(
            definition_source=ProcessorPipeline.get_required_config(),
            values_source_list=[],
        )
        config = cm.get_config()
        config.database_class = mock.Mock()
        config.sentry = mock.Mock()
        config.processor_name = "dwight"
        return config

    @mock.patch("socorro.lib.sentry_client.get_hub", side_effect=Exception("fail"))
    @mock.patch("socorro.lib.sentry_client.is_enabled", return_value=False)
    def test_rule_error_sentry_disabled(self, is_enabled, mock_get_hub):
        config = self.get_config()

        # Test with Sentry disabled (no dsn set)
        raw_crash = {"uuid": "1"}
        processed_crash = DotDict()

        processor = ProcessorPipeline(config, rules=[BadRule()])
        processor.process_crash(raw_crash, {}, processed_crash)

        # Notes were added
        assert (
            processed_crash.processor_notes
            == "dwight; ProcessorPipeline; rule BadRule failed: KeyError"
        )
        mock_get_hub.assert_not_called()

    @mock.patch("socorro.lib.sentry_client.get_hub")
    @mock.patch("socorro.lib.sentry_client.is_enabled", return_value=True)
    def test_rule_error_sentry_enabled(self, is_enabled, mock_get_hub):
        config = self.get_config()
        captured_exceptions = []  # a global

        def mock_capture_exception(error):
            captured_exceptions.append(error[1])
            return "someidentifier"

        hub = mock.MagicMock()

        def mock_Hub():
            hub.capture_exception.side_effect = mock_capture_exception
            return hub

        mock_get_hub.side_effect = mock_Hub

        # Test with Sentry enabled (dsn set)
        raw_crash = {"uuid": "1"}
        processed_crash = DotDict()

        processor = ProcessorPipeline(config, rules=[BadRule()])
        processor.process_crash(raw_crash, {}, processed_crash)

        # Notes were added again
        assert (
            processed_crash.processor_notes
            == "dwight; ProcessorPipeline; rule BadRule failed: KeyError"
        )
        assert isinstance(captured_exceptions[0], KeyError)

    def test_process_crash_existing_processed_crash(self):
        raw_crash = DotDict({"uuid": "1"})
        raw_dumps = {}
        processed_crash = DotDict(
            {
                "processor_notes": "we've been here before; yep",
                "started_datetime": "2014-01-01T00:00:00",
            }
        )

        p = ProcessorPipeline(self.get_config(), rules=[CPUInfoRule(), OSInfoRule()])
        with mock.patch("socorro.processor.processor_pipeline.utc_now") as faked_utcnow:
            faked_utcnow.return_value = "2015-01-01T00:00:00"
            processed_crash = p.process_crash(raw_crash, raw_dumps, processed_crash)

        assert processed_crash.success
        assert processed_crash.started_datetime == "2015-01-01T00:00:00"
        assert processed_crash.startedDateTime == "2015-01-01T00:00:00"
        assert processed_crash.completed_datetime == "2015-01-01T00:00:00"
        assert processed_crash.completeddatetime == "2015-01-01T00:00:00"
        expected = (
            "dwight; ProcessorPipeline; earlier processing: 2014-01-01T00:00:00;"
            " we've been here before; yep"
        )
        assert processed_crash.processor_notes == expected
