# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import ANY

import freezegun
from fillmore.test import diff_structure

from socorro.lib.libdatetime import date_to_string, utc_now
from socorro.processor.processor_app import ProcessorApp
from socorro.processor.pipeline import Pipeline
from socorro.processor.rules.general import CPUInfoRule, OSInfoRule
from socorro.processor.rules.base import Rule


class BadRule(Rule):
    def action(self, *args, **kwargs):
        raise KeyError("pii")


# NOTE(willkg): If this changes, we should update it and look for new things that should
# be scrubbed. Use ANY for things that change between tests like timestamps, source code
# data (line numbers, file names, post/pre_context), event ids, build ids, versions,
# etc.
RULE_ERROR_EVENT = {
    "breadcrumbs": ANY,
    "contexts": {
        "runtime": {
            "build": ANY,
            "name": "CPython",
            "version": ANY,
        },
        "trace": {
            "parent_span_id": None,
            "span_id": ANY,
            "trace_id": ANY,
        },
    },
    "environment": "production",
    "event_id": ANY,
    "exception": {
        "values": [
            {
                "mechanism": {"handled": True, "type": "generic"},
                "module": None,
                "stacktrace": {
                    "frames": [
                        {
                            "abs_path": "/app/socorro/processor/pipeline.py",
                            "context_line": ANY,
                            "filename": "socorro/processor/pipeline.py",
                            "function": "process_crash",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "socorro.processor.pipeline",
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
                            "abs_path": "/app/socorro/tests/processor/test_pipeline.py",
                            "context_line": ANY,
                            "filename": "socorro/tests/processor/test_pipeline.py",
                            "function": "action",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "socorro.tests.processor.test_pipeline",
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
        "rule": "socorro.tests.processor.test_pipeline.BadRule",
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
        "packages": [{"name": "pypi:sentry-sdk", "version": ANY}],
        "version": ANY,
    },
    "server_name": ANY,
    "timestamp": ANY,
    "transaction_info": {},
}


class TestPipeline:
    def test_rule_error(self, tmp_path, sentry_helper):
        ProcessorApp()._set_up_sentry()

        # Test with Sentry enabled (dsn set)
        raw_crash = {"uuid": "7c67ad15-518b-4ccb-9be0-6f4c82220721"}
        processed_crash = {}

        rulesets = {"default": [BadRule()]}
        processor = Pipeline(rulesets=rulesets, hostname="testhost")

        with sentry_helper.reuse() as sentry_client:
            processor.process_crash("default", raw_crash, {}, processed_crash, tmp_path)

            # Notes were added again
            notes = processed_crash["processor_notes"].split("\n")
            assert notes[1] == (
                "ruleset 'default' "
                + "rule 'socorro.tests.processor.test_pipeline.BadRule' "
                + "failed: KeyError"
            )

            (event,) = sentry_client.envelope_payloads

            # Assert that the event is what we expected
            differences = diff_structure(event, RULE_ERROR_EVENT)
            assert differences == []

    def test_process_crash_existing_processed_crash(self, tmp_path):
        raw_crash = {"uuid": "1"}
        dumps = {}
        processed_crash = {"processor_notes": "previousnotes"}

        rulesets = {"default": [CPUInfoRule(), OSInfoRule()]}
        pipeline = Pipeline(rulesets=rulesets, hostname="testhost")

        now = utc_now()
        with freezegun.freeze_time(now):
            processed_crash = pipeline.process_crash(
                ruleset_name="default",
                raw_crash=raw_crash,
                dumps=dumps,
                processed_crash=processed_crash,
                tmpdir=str(tmp_path),
            )

        assert processed_crash["success"] is True
        assert processed_crash["started_datetime"] == date_to_string(now)
        assert processed_crash["completed_datetime"] == date_to_string(now)
        assert "previousnotes" not in processed_crash["processor_notes"]
        processor_history = "".join(processed_crash["processor_history"])
        assert "previousnotes" in processor_history
