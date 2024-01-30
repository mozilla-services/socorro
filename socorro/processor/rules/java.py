# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro.processor.rules.base import Rule

from socorro.lib import libjava


class JavaStackTraceRule(Rule):
    """Process and sanitize JavaStackTrace annotation."""

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return bool(raw_crash.get("JavaStackTrace", None))

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        java_stack_trace_raw = raw_crash["JavaStackTrace"]

        # The java_stack_trace_raw version can contain PII in the exception message
        # and should be treated as protected data
        processed_crash["java_stack_trace_raw"] = java_stack_trace_raw

        # Add java_stack_trace field to processed crash which is a sanitized
        # version of java_stack_trace_raw
        try:
            parsed_java_stack_trace = libjava.parse_java_stack_trace(
                java_stack_trace_raw
            )
            java_stack_trace = parsed_java_stack_trace.to_public_string()
        except libjava.MalformedJavaStackTrace:
            status.add_note("JavaStackTrace: malformed JavaStackTrace")
            java_stack_trace = "malformed"

        processed_crash["java_stack_trace"] = java_stack_trace
