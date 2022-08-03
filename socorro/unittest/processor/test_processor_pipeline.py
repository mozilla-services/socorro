# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os
from pathlib import Path
from unittest.mock import ANY

from configman import ConfigurationManager
from configman.dotdict import DotDict
import freezegun

from socorro.lib.libdatetime import utc_now
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

    # We need the same configuration of Sentry as what the ProcessorApp creates
    ProcessorApp.configure_sentry(
        basedir=basedir,
        host_id="test_processor",
        sentry_dsn=sentry_dsn,
    )


# NOTE(willkg): If this changes, we should update it and look for new things that should
# be scrubbed. Use ANY for things that change between tests.
RULE_ERROR_EVENT = {
    "breadcrumbs": {"values": []},
    "contexts": {
        "runtime": {
            "build": ANY,
            "name": "CPython",
            "version": ANY,
        }
    },
    "environment": "production",
    "event_id": ANY,
    "exception": {
        "values": [
            {
                "mechanism": None,
                "module": None,
                "stacktrace": {
                    "frames": [
                        {
                            "abs_path": "/app/socorro/processor/processor_pipeline.py",
                            "context_line": ANY,
                            "filename": "socorro/processor/processor_pipeline.py",
                            "function": "process_crash",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "socorro.processor.processor_pipeline",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/app/socorro/processor/rules/base.py",
                            "context_line": ANY,
                            "filename": "socorro/processor/rules/base.py",
                            "function": "act",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "socorro.processor.rules.base",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/app/socorro/unittest/processor/test_processor_pipeline.py",
                            "context_line": ANY,
                            "filename": "socorro/unittest/processor/test_processor_pipeline.py",
                            "function": "action",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "socorro.unittest.processor.test_processor_pipeline",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                    ]
                },
                "type": "KeyError",
                "value": "'pii'",
            }
        ]
    },
    "extra": {
        "rule": "socorro.unittest.processor.test_processor_pipeline.BadRule",
    },
    "level": "error",
    "modules": ANY,
    "platform": "python",
    "release": ANY,
    "sdk": {
        "integrations": [
            "atexit",
            "boto3",
            "dedupe",
            "excepthook",
            "modules",
            "stdlib",
            "threading",
        ],
        "name": "sentry.python",
        "packages": [{"name": "pypi:sentry-sdk", "version": "1.9.0"}],
        "version": "1.9.0",
    },
    "server_name": "test_processor",
    "timestamp": ANY,
    "transaction_info": {},
}


class TestProcessorPipeline:
    def get_config(self):
        # Retrieve config for a ProcessorPipeline
        cm = ConfigurationManager(
            definition_source=ProcessorPipeline.get_required_config(),
            values_source_list=[],
        )
        config = cm.get_config()
        return config

    def test_rule_error(self, sentry_helper):
        set_up_sentry()

        with sentry_helper.reuse() as sentry_client:
            config = self.get_config()

            # Test with Sentry enabled (dsn set)
            raw_crash = {"uuid": "7c67ad15-518b-4ccb-9be0-6f4c82220721"}
            processed_crash = DotDict()

            processor = ProcessorPipeline(config, rules={"default": [BadRule()]})
            processor.process_crash("default", raw_crash, {}, processed_crash)

            # Notes were added again
            notes = processed_crash["processor_notes"].split("\n")
            assert notes[1] == (
                "ruleset 'default' "
                + "rule 'socorro.unittest.processor.test_processor_pipeline.BadRule' "
                + "failed: KeyError"
            )

            (event,) = sentry_client.events

            # If this test fails, this will print out the new event that you can copy
            # and paste and then edit above
            print(json.dumps(event, indent=4, sort_keys=True))

            # Assert that there are no frame-local variables
            assert event == RULE_ERROR_EVENT

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
