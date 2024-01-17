# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro.processor.pipeline import Status
from socorro.processor.rules.java import JavaStackTraceRule


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
