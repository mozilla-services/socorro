# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.lib import libjava

EXC = """\
Exception: msg
\tat org.File.function(File.java:100)
\tat org.File.function2(File.java:200)
"""

EXC_NO_MESSAGE = """\
Exception
\tat org.File.function(File.java:100)
\tat org.File.function2(File.java:200)
"""

EXC_WITH_MULTILINE_MSG = """\
android.database.sqlite.SQLiteDatabaseLockedException: database is locked (code 5)
#################################################################
Error Code : 5 (SQLITE_BUSY)
Caused By : The database file is locked.
\t(database is locked (code 5))
#################################################################
\tat android.database.sqlite.SQLiteConnection.nativeExecuteForChangedRowCount(Native Method)
\tat android.database.sqlite.SQLiteConnection.executeForChangedRowCount(SQLiteConnection.java:904)
"""

EXC_WITH_SUPPRESSED = """\
Exception: msg
\tat org.File.function(File.java:100)
\tSuppressed: Exception2: msg2
\t\tat org.File.function(File.java:101)
"""

EXC_WITH_CAUSED_BY = """\
Exception: msg
\tat org.File.function(File.java:100)
\tCaused by: Exception2: msg2; no stack trace available
"""

EXC_WITH_UNINDENTED_CAUSED_BY = """\
Exception: msg
\tat org.File.function(File.java:100)
Caused by: Exception2: msg2; no stack trace available
"""

EXC_MSG_WITH_PARENS = """\
Exception: Error(

General Error: "No subscriptions created yet.")
\tat org.File.function(RustError.kt:4)
"""


class Test_parse_java_stack_trace:
    def test_parse_basic(self):
        """Parse a basic exception with a class, message, and some stack lines"""
        java_exc = libjava.parse_java_stack_trace(EXC)
        assert java_exc.exception_class == "Exception"
        assert java_exc.exception_message == "msg"
        assert java_exc.stack == [
            "at org.File.function(File.java:100)",
            "at org.File.function2(File.java:200)",
        ]
        assert java_exc.additional == []

    def test_no_message(self):
        """Parse a basic exception with a class, message, and some stack lines"""
        java_exc = libjava.parse_java_stack_trace(EXC_NO_MESSAGE)
        assert java_exc.exception_class == "Exception"
        assert java_exc.exception_message == ""
        assert java_exc.stack == [
            "at org.File.function(File.java:100)",
            "at org.File.function2(File.java:200)",
        ]
        assert java_exc.additional == []

        assert java_exc.to_public_string() == (
            "Exception\n"
            "\tat org.File.function(File.java:100)\n"
            "\tat org.File.function2(File.java:200)"
        )

    def test_parse_multi_line_msg(self):
        """Parse an exception where the exception message is multiple lines"""
        java_exc = libjava.parse_java_stack_trace(EXC_WITH_MULTILINE_MSG)
        assert (
            java_exc.exception_class
            == "android.database.sqlite.SQLiteDatabaseLockedException"
        )
        assert (
            java_exc.exception_message == "database is locked (code 5)\n"
            "#################################################################\n"
            "Error Code : 5 (SQLITE_BUSY)\n"
            "Caused By : The database file is locked.\n"
            "\t(database is locked (code 5))\n"
            "#################################################################"
        )
        assert java_exc.stack == [
            "at android.database.sqlite.SQLiteConnection.nativeExecuteForChangedRowCount(Native Method)",  # noqa
            "at android.database.sqlite.SQLiteConnection.executeForChangedRowCount(SQLiteConnection.java:904)",  # noqa
        ]
        assert java_exc.additional == []

    def test_parse_suppressed(self):
        """Parse an exception with a "Suppressed" section"""
        java_exc = libjava.parse_java_stack_trace(EXC_WITH_SUPPRESSED)
        assert java_exc.exception_class == "Exception"
        assert java_exc.exception_message == "msg"
        assert java_exc.stack == ["at org.File.function(File.java:100)"]
        assert java_exc.additional == [
            "\tSuppressed: Exception2: msg2",
            "\t\tat org.File.function(File.java:101)",
        ]

    def test_parse_caused_by(self):
        """Parse an exception with a "Caused by" section with no stack"""
        java_exc = libjava.parse_java_stack_trace(EXC_WITH_CAUSED_BY)
        assert java_exc.exception_class == "Exception"
        assert java_exc.exception_message == "msg"
        assert java_exc.stack == ["at org.File.function(File.java:100)"]
        assert java_exc.additional == [
            "\tCaused by: Exception2: msg2; no stack trace available"
        ]

    def test_parse_unindented_caused_by(self):
        """Parse an exception with an unindented "Caused by" section."""
        java_exc = libjava.parse_java_stack_trace(EXC_WITH_UNINDENTED_CAUSED_BY)
        assert java_exc.exception_class == "Exception"
        assert java_exc.exception_message == "msg"
        assert java_exc.stack == ["at org.File.function(File.java:100)"]
        assert java_exc.additional == [
            "Caused by: Exception2: msg2; no stack trace available"
        ]

    def test_parenthesized_msg(self):
        """Parse an exception with a exception message in parentheses."""
        java_exc = libjava.parse_java_stack_trace(EXC_MSG_WITH_PARENS)
        assert java_exc.exception_class == "Exception"
        assert (
            java_exc.exception_message
            == 'Error(\n\nGeneral Error: "No subscriptions created yet.")'
        )
        assert java_exc.stack == ["at org.File.function(RustError.kt:4)"]
        assert java_exc.additional == []

    @pytest.mark.parametrize(
        "text",
        [
            # No text blob
            None,
            "",
            # Line without a tab in STACK stage
            ("Exception: msg\n\tat org.File.function(File.java:100)\nbadline"),
        ],
    )
    def test_malformed(self, text):
        with pytest.raises(libjava.MalformedJavaStackTrace):
            libjava.parse_java_stack_trace(text)


# Reference `processed_crash.java_exception` value from a real Fenix crash with the
# signature "java.lang.RuntimeException: at
# android.app.servertransaction.PendingTransactionActions$StopInfo.run(PendingTransactionActions.java)",
# with frames trimmed to 4 per exception.
# It includes:
# - a chain of two exceptions: values[0] is the root cause
#   (TransactionTooLargeException) and values[1], the last element, is the outermost
#   exception (RuntimeException)
# - a nested class in a frame module: PendingTransactionActions$StopInfo
# - a native frame (lineno: -2) in the root cause
# - a package-level exception class: java.lang package with a RuntimeException, joined with "."
# See also `java_exception` in processed_crash.schema.yaml.
JAVA_EXCEPTION_FIXTURE = {
    "exception": {
        "values": [
            {
                "stacktrace": {
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
                        {
                            "module": "android.app.IActivityClientController$Stub$Proxy",
                            "function": "activityStopped",
                            "in_app": True,
                            "lineno": 1459,
                            "filename": "IActivityClientController.java",
                        },
                        {
                            "module": "android.app.ActivityClient",
                            "function": "activityStopped",
                            "in_app": True,
                            "lineno": 112,
                            "filename": "ActivityClient.java",
                        },
                    ],
                    "type": "TransactionTooLargeException",
                    "module": "android.os",
                }
            },
            {
                "stacktrace": {
                    "frames": [
                        {
                            "module": "android.app.servertransaction.PendingTransactionActions$StopInfo",
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
                        {
                            "module": "android.os.Handler",
                            "function": "dispatchMessage",
                            "in_app": True,
                            "lineno": 99,
                            "filename": "Handler.java",
                        },
                        {
                            "module": "android.os.Looper",
                            "function": "loopOnce",
                            "in_app": True,
                            "lineno": 222,
                            "filename": "Looper.java",
                        },
                    ],
                    "type": "RuntimeException",
                    "module": "java.lang",
                }
            },
        ]
    }
}

JAVA_STACK_TRACE_FROM_JAVA_EXCEPTION_FIXTURE = (
    "java.lang.RuntimeException\n"
    "\tat android.app.servertransaction.PendingTransactionActions$StopInfo.run(PendingTransactionActions.java:146)\n"  # noqa
    "\tat android.os.Handler.handleCallback(Handler.java:958)\n"
    "\tat android.os.Handler.dispatchMessage(Handler.java:99)\n"
    "\tat android.os.Looper.loopOnce(Looper.java:222)"
)


def make_java_exception(*stacktraces):
    """Build a java_exception value with one entry per stacktrace, in the order given."""
    return {
        "exception": {
            "values": [{"stacktrace": stacktrace} for stacktrace in stacktraces]
        }
    }


def make_frame(**kwargs):
    """Build a frame with some defaults. Pass {key}=None to omit a key."""
    frame = {
        "module": "android.os.Handler",
        "function": "dispatchMessage",
        "lineno": 99,
        "filename": "Handler.java",
    }
    frame.update(kwargs)
    return {key: value for key, value in frame.items() if value is not None}


class Test_java_stack_trace_from_java_exception:
    def test_reference_crash(self):
        result = libjava.java_stack_trace_from_java_exception(JAVA_EXCEPTION_FIXTURE)
        assert result == JAVA_STACK_TRACE_FROM_JAVA_EXCEPTION_FIXTURE

    def test_uses_last_exception(self):
        """
        Ensure we use the last exception in the exception chain to create the first
        line in java_stack_trace.
        """
        java_exception = make_java_exception(
            {
                "module": "java.lang",
                "type": "IllegalStateException",
                "frames": [make_frame()],
            },
            {
                "module": "java.lang",
                "type": "RuntimeException",
                "frames": [make_frame()],
            },
        )
        result = libjava.java_stack_trace_from_java_exception(java_exception)
        assert result.splitlines()[0] == "java.lang.RuntimeException"

    @pytest.mark.parametrize(
        "java_exception",
        [
            None,
            {},
            {"exception": {}},
            {"exception": {"values": []}},
            {"exception": {"values": [{}]}},
            # Can't build a class name without both module and type
            make_java_exception({"type": "RuntimeException", "frames": [make_frame()]}),
            make_java_exception({"module": "java.lang", "frames": [make_frame()]}),
            make_java_exception({"module": "", "type": "", "frames": [make_frame()]}),
        ],
    )
    def test_returns_none(self, java_exception):
        assert libjava.java_stack_trace_from_java_exception(java_exception) is None

    @pytest.mark.parametrize(
        "module, exception_type, expected",
        [
            # Package-level class
            ("java.lang", "RuntimeException", "java.lang.RuntimeException"),
            # Nested class: Kotlin's "." is turned back into Java's "$"
            (
                "android.view.WindowManager",
                "BadTokenException",
                "android.view.WindowManager$BadTokenException",
            ),
        ],
    )
    def test_exception_class(self, module, exception_type, expected):
        java_exception = make_java_exception(
            {"module": module, "type": exception_type, "frames": []}
        )
        result = libjava.java_stack_trace_from_java_exception(java_exception)
        assert result == expected

    @pytest.mark.parametrize(
        "stacktrace",
        [
            pytest.param(
                {"module": "java.lang", "type": "OutOfMemoryError", "frames": []},
                id="empty-frames",
            ),
            pytest.param(
                {"module": "java.lang", "type": "OutOfMemoryError"},
                id="missing-frames",
            ),
        ],
    )
    def test_no_frames(self, stacktrace):
        """No frames: java_stack_trace is just the class name"""
        result = libjava.java_stack_trace_from_java_exception(
            make_java_exception(stacktrace)
        )
        assert result == "java.lang.OutOfMemoryError"

    @pytest.mark.parametrize(
        "frame, expected",
        [
            (make_frame(), "at android.os.Handler.dispatchMessage(Handler.java:99)"),
            # Native method: lineno == -2, even if there's a filename
            (
                make_frame(
                    module="android.os.BinderProxy",
                    function="transactNative",
                    filename="BinderProxy.java",
                    lineno=-2,
                ),
                "at android.os.BinderProxy.transactNative(Native Method)",
            ),
            # No filename: Unknown Source, even if there's a line number
            (
                make_frame(
                    module="kotlinx.coroutines.BuildersKt",
                    function="withContext",
                    filename=None,
                    lineno=92,
                ),
                "at kotlinx.coroutines.BuildersKt.withContext(Unknown Source)",
            ),
            (
                make_frame(
                    module="kotlinx.coroutines.BuildersKt",
                    function="withContext",
                    filename=None,
                    lineno=None,
                ),
                "at kotlinx.coroutines.BuildersKt.withContext(Unknown Source)",
            ),
            # Filename but no usable line number
            (
                make_frame(lineno=None),
                "at android.os.Handler.dispatchMessage(Handler.java)",
            ),
            (
                make_frame(lineno=-1),
                "at android.os.Handler.dispatchMessage(Handler.java)",
            ),
            # Kotlin and R8 synthetic frames keep their line numbers
            (
                make_frame(
                    module="mozilla.appservices.autofill.FfiConverterTypeAutofillApiError",
                    function="read",
                    filename="autofill.kt",
                    lineno=16,
                ),
                "at mozilla.appservices.autofill.FfiConverterTypeAutofillApiError.read(autofill.kt:16)",  # noqa
            ),
            (
                make_frame(
                    module="mozilla.components.browser.engine.gecko.GeckoEngine$$ExternalSyntheticLambda36",  # noqa
                    function="onShutdown",
                    filename="R8$$SyntheticClass",
                    lineno=5,
                ),
                "at mozilla.components.browser.engine.gecko.GeckoEngine$$ExternalSyntheticLambda36.onShutdown(R8$$SyntheticClass:5)",  # noqa
            ),
            # Only module or only function
            (make_frame(function=None), "at android.os.Handler(Handler.java:99)"),
            (make_frame(module=None), "at dispatchMessage(Handler.java:99)"),
            # Neither module nor function
            (make_frame(module=None, function=None), "at (Handler.java:99)"),
        ],
    )
    def test_frame(self, frame, expected):
        java_exception = make_java_exception(
            {"module": "java.lang", "type": "RuntimeException", "frames": [frame]}
        )
        result = libjava.java_stack_trace_from_java_exception(java_exception)
        assert result == f"java.lang.RuntimeException\n\t{expected}"

    def test_frame_order(self):
        """frames[0] is the top frame, so it becomes line 2 (line 1 is the exception class)"""
        java_exception = make_java_exception(
            {
                "module": "java.lang",
                "type": "RuntimeException",
                "frames": [
                    make_frame(function="handleCallback", lineno=958),
                    make_frame(function="dispatchMessage", lineno=99),
                ],
            }
        )
        result = libjava.java_stack_trace_from_java_exception(java_exception)
        assert result.splitlines()[1:] == [
            "\tat android.os.Handler.handleCallback(Handler.java:958)",
            "\tat android.os.Handler.dispatchMessage(Handler.java:99)",
        ]
