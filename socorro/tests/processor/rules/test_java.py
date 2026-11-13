# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy

import pytest

from socorro.processor.pipeline import Status
from socorro.processor.rules.java import (
    JavaStackTraceFromJavaExceptionRule,
    JavaStackTraceRule,
)
from socorro.signature.rules import JavaSignatureTool


class TestJavaStackTraceRule:
    def test_javastacktrace(self, tmp_path):
        raw_crash = {
            "JavaStackTrace": (
                "Exception: some messge\n"
                + "\tat org.File.function(File.java:100)\n"
                + "\tCaused by: Exception: some other message\n"
                + "\t\tat org.File.function(File.java:100)"
            )
        }
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = JavaStackTraceRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        # The entire JavaStackTrace blob
        assert processed_crash["java_stack_trace_raw"] == raw_crash["JavaStackTrace"]

        # Everything except the exception message and "Caused by" section
        # which can contain PII
        assert (
            processed_crash["java_stack_trace"]
            == "Exception\n\tat org.File.function(File.java:100)"
        )

    def test_malformed_javastacktrace(self, tmp_path):
        raw_crash = {"JavaStackTrace": "junk\n\tat org.File.function\njunk"}

        dumps = {}
        processed_crash = {}
        status = Status()

        rule = JavaStackTraceRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        # The entire JavaStackTrace blob
        assert processed_crash["java_stack_trace_raw"] == raw_crash["JavaStackTrace"]

        # The data is malformed, so this should just show "malformed"
        assert processed_crash["java_stack_trace"] == "malformed"

        # Make sure there's a note in the notes about it
        assert "malformed JavaStackTrace" in status.notes[0]


# A java_exception with a chain of two exceptions (root cause first, outermost
# exception last), based on a real Fenix crash with the signature
# "java.lang.RuntimeException: at
# android.app.servertransaction.PendingTransactionActions$StopInfo.run(PendingTransactionActions.java)",
# with frames trimmed to 2 per exception.
JAVA_EXCEPTION = {
    "exception": {
        "values": [
            {
                "stacktrace": {
                    "module": "android.os",
                    "type": "TransactionTooLargeException",
                    "frames": [
                        {
                            "module": "android.os.BinderProxy",
                            "function": "transactNative",
                            "in_app": False,
                            "lineno": -2,
                            "filename": "BinderProxy.java",
                        },
                        {
                            "module": "android.os.BinderProxy",
                            "function": "transact",
                            "in_app": True,
                            "lineno": 639,
                            "filename": "BinderProxy.java",
                        },
                    ],
                }
            },
            {
                "stacktrace": {
                    "module": "java.lang",
                    "type": "RuntimeException",
                    "frames": [
                        {
                            "module": "android.app.servertransaction.PendingTransactionActions$StopInfo",  # noqa
                            "function": "run",
                            "in_app": True,
                            "lineno": 146,
                            "filename": "PendingTransactionActions.java",
                        },
                        {
                            "module": "android.os.Handler",
                            "function": "handleCallback",
                            "in_app": True,
                            "lineno": 958,
                            "filename": "Handler.java",
                        },
                    ],
                }
            },
        ]
    }
}

JAVA_STACK_TRACE = (
    "java.lang.RuntimeException\n"
    "\tat android.app.servertransaction.PendingTransactionActions$StopInfo.run(PendingTransactionActions.java:146)\n"  # noqa
    "\tat android.os.Handler.handleCallback(Handler.java:958)"
)


class TestJavaStackTraceFromJavaExceptionRule:
    def run_rule(self, processed_crash, tmp_path):
        status = Status()
        rule = JavaStackTraceFromJavaExceptionRule()
        rule.act({}, {}, processed_crash, str(tmp_path), status)
        return status

    def test_builds_java_stack_trace_for_ping(self, tmp_path):
        processed_crash = {
            "submission_type": "ping",
            "java_exception": copy.deepcopy(JAVA_EXCEPTION),
        }
        status = self.run_rule(processed_crash, tmp_path)

        assert processed_crash["java_stack_trace"] == JAVA_STACK_TRACE
        # The raw, protected version only comes from the JavaStackTrace annotation
        assert "java_stack_trace_raw" not in processed_crash
        assert status.notes == [
            "JavaStackTraceFromJavaExceptionRule: built java_stack_trace from "
            + "java_exception"
        ]

    def test_signature_matches_crash_report(self, tmp_path):
        """The built java_stack_trace gives the same signature as the crash report"""
        processed_crash = {
            "submission_type": "ping",
            "java_exception": copy.deepcopy(JAVA_EXCEPTION),
        }
        self.run_rule(processed_crash, tmp_path)

        signature = JavaSignatureTool().generate(processed_crash["java_stack_trace"])[0]
        assert signature == (
            "java.lang.RuntimeException: at "
            "android.app.servertransaction.PendingTransactionActions$StopInfo.run(PendingTransactionActions.java)"  # noqa
        )

    @pytest.mark.parametrize(
        "submission_type",
        [
            pytest.param("report", id="report"),
            pytest.param(None, id="missing-submission-type"),
        ],
    )
    def test_skips_non_ping(self, submission_type, tmp_path):
        processed_crash = {"java_exception": copy.deepcopy(JAVA_EXCEPTION)}
        if submission_type is not None:
            processed_crash["submission_type"] = submission_type
        status = self.run_rule(processed_crash, tmp_path)

        assert "java_stack_trace" not in processed_crash
        assert status.notes == []

    def test_does_not_overwrite_java_stack_trace(self, tmp_path):
        processed_crash = {
            "submission_type": "ping",
            "java_exception": copy.deepcopy(JAVA_EXCEPTION),
            "java_stack_trace": "existing value",
        }
        status = self.run_rule(processed_crash, tmp_path)

        assert processed_crash["java_stack_trace"] == "existing value"
        assert status.notes == []

    def test_skips_without_java_exception(self, tmp_path):
        processed_crash = {"submission_type": "ping"}
        status = self.run_rule(processed_crash, tmp_path)

        assert "java_stack_trace" not in processed_crash
        assert status.notes == []

    def test_cannot_build_java_stack_trace(self, tmp_path):
        """If java_exception can't be used, leave java_stack_trace unset"""
        processed_crash = {
            "submission_type": "ping",
            # No module or type, so there's no exception class name
            "java_exception": {
                "exception": {"values": [{"stacktrace": {"frames": []}}]}
            },
        }
        status = self.run_rule(processed_crash, tmp_path)

        assert "java_stack_trace" not in processed_crash
        assert status.notes == [
            "JavaStackTraceFromJavaExceptionRule: could not build java_stack_trace"
        ]
