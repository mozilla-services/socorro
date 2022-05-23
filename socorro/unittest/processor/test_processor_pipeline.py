# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from pathlib import Path
import time
from unittest import mock

from configman import ConfigurationManager
from configman.dotdict import DotDict
import freezegun
import requests

from socorro.lib.libdatetime import utc_now
from socorro.lib.libsentry import get_sentry_base_url
from socorro.processor.processor_app import ProcessorApp
from socorro.processor.processor_pipeline import ProcessorPipeline
from socorro.processor.rules.general import CPUInfoRule, OSInfoRule
from socorro.processor.rules.base import Rule


class BadRule(Rule):
    def action(self, *args, **kwargs):
        raise KeyError("pii")


def set_up_sentry():
    """Sets up sentry using SENTRY_DSN"""
    # FIXME(willkg): SENTRY_DSN is where we're putting the SENTRY_DSN even if there
    # are components that are configured in other ways.
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if not sentry_dsn:
        raise Exception("SENTRY_DSN is not defined in os.environ")

    # This basedir is relative to this file
    basedir = Path(__file__).resolve().parent.parent.parent
    # NOTE(willkg): This is a fixture for sentry set up by the processor, so we can
    # use the ProcessorApp set up class method
    ProcessorApp.set_up_sentry(
        basedir=basedir,
        host_id="test_processor",
        sentry_dsn=sentry_dsn,
    )


class TestProcessorPipeline:
    def get_config(self):
        # Retrieve config for a ProcessorPipeline
        cm = ConfigurationManager(
            definition_source=ProcessorPipeline.get_required_config(),
            values_source_list=[],
        )
        config = cm.get_config()
        return config

    @mock.patch("socorro.lib.libsentry.get_hub", side_effect=Exception("fail"))
    @mock.patch("socorro.lib.libsentry.is_enabled", return_value=False)
    def test_rule_error_sentry_disabled(self, is_enabled, mock_get_hub):
        config = self.get_config()

        # Test with Sentry disabled (no dsn set)
        raw_crash = {"uuid": "1"}
        processed_crash = DotDict()

        processor = ProcessorPipeline(config, rules={"default": [BadRule()]})
        processor.process_crash("default", raw_crash, {}, processed_crash)

        # Notes were added
        notes = processed_crash["processor_notes"].split("\n")
        assert notes[1] == "rule BadRule failed: KeyError"
        mock_get_hub.assert_not_called()

    def test_rule_error_sentry_enabled(self):
        set_up_sentry()
        sentry_dsn = os.environ.get("SENTRY_DSN")

        fakesentry_api = get_sentry_base_url(sentry_dsn)

        # Flush errors so the list is empty
        resp = requests.post(fakesentry_api + "api/flush/")
        assert resp.status_code == 200

        resp = requests.get(fakesentry_api + "api/errorlist/")
        assert len(resp.json()["errors"]) == 0

        config = self.get_config()

        # Test with Sentry enabled (dsn set)
        raw_crash = {"uuid": "1"}
        processed_crash = DotDict()

        processor = ProcessorPipeline(config, rules={"default": [BadRule()]})
        processor.process_crash("default", raw_crash, {}, processed_crash)

        # Pause here to let sentry send the event and fakesentry to get it
        time.sleep(1)

        # Notes were added again
        notes = processed_crash["processor_notes"].split("\n")
        assert notes[1] == "rule BadRule failed: KeyError"

        resp = requests.get(fakesentry_api + "api/errorlist/")
        assert len(resp.json()["errors"]) == 1
        error_id = resp.json()["errors"][0]

        resp = requests.get(f"{fakesentry_api}api/error/{error_id}")
        payload = resp.json()["payload"]

        # Assert that raw_crash and processed_crash variables are scrubbed
        is_raw_crash_scrubbed = False
        is_processed_crash_scrubbed = False
        for exception in payload["exception"]["values"]:
            for frame in exception["stacktrace"]["frames"]:
                if "raw_crash" in frame["vars"]:
                    assert frame["vars"]["raw_crash"] == "[Scrubbed]"
                    is_raw_crash_scrubbed = True
                if "processed_crash" in frame["vars"]:
                    assert frame["vars"]["processed_crash"] == "[Scrubbed]"
                    is_processed_crash_scrubbed = True

        assert is_raw_crash_scrubbed is True
        assert is_processed_crash_scrubbed is True

    def test_process_crash_existing_processed_crash(self):
        raw_crash = DotDict({"uuid": "1"})
        dumps = {}
        processed_crash = DotDict(
            {
                "processor_notes": "previousnotes",
            }
        )

        pipeline = ProcessorPipeline(
            self.get_config(), rules={"default": [CPUInfoRule(), OSInfoRule()]}
        )

        now = utc_now()
        with freezegun.freeze_time(now):
            processed_crash = pipeline.process_crash(
                ruleset_name="default",
                raw_crash=raw_crash,
                dumps=dumps,
                processed_crash=processed_crash,
            )

        assert processed_crash.success
        assert processed_crash.started_datetime == now
        assert processed_crash.completed_datetime == now
        notes = processed_crash["processor_notes"].split("\n")
        assert ">>> Start processing" in notes[0]
        assert "previousnotes" in notes
