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


def test_parse_basic():
    """Parse a basic exception with a class, message, and some stack lines"""
    java_exc = libjava.parse_java_stack_trace(EXC)
    assert java_exc.exception_class == "Exception"
    assert java_exc.exception_message == "msg"
    assert java_exc.stack == [
        "at org.File.function(File.java:100)",
        "at org.File.function2(File.java:200)",
    ]
    assert java_exc.additional == []


EXC_NO_MESSAGE = """\
Exception
\tat org.File.function(File.java:100)
\tat org.File.function2(File.java:200)
"""


def test_no_message():
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


def test_parse_multi_line_msg():
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


EXC_WITH_SUPPRESSED = """\
Exception: msg
\tat org.File.function(File.java:100)
\tSuppressed: Exception2: msg2
\t\tat org.File.function(File.java:101)
"""


def test_parse_suppressed():
    """Parse an exception with a "Suppressed" section"""
    java_exc = libjava.parse_java_stack_trace(EXC_WITH_SUPPRESSED)
    assert java_exc.exception_class == "Exception"
    assert java_exc.exception_message == "msg"
    assert java_exc.stack == ["at org.File.function(File.java:100)"]
    assert java_exc.additional == [
        "\tSuppressed: Exception2: msg2",
        "\t\tat org.File.function(File.java:101)",
    ]


EXC_WITH_CAUSED_BY = """\
Exception: msg
\tat org.File.function(File.java:100)
\tCaused by: Exception2: msg2; no stack trace available
"""


def test_parse_caused_by():
    """Parse an exception with a "Caused by" section with no stack"""
    java_exc = libjava.parse_java_stack_trace(EXC_WITH_CAUSED_BY)
    assert java_exc.exception_class == "Exception"
    assert java_exc.exception_message == "msg"
    assert java_exc.stack == ["at org.File.function(File.java:100)"]
    assert java_exc.additional == [
        "\tCaused by: Exception2: msg2; no stack trace available"
    ]


EXC_WITH_UNINDENTED_CAUSED_BY = """\
Exception: msg
\tat org.File.function(File.java:100)
Caused by: Exception2: msg2; no stack trace available
"""


def test_parse_unindented_caused_by():
    """Parse an exception with an unindented "Caused by" section."""
    java_exc = libjava.parse_java_stack_trace(EXC_WITH_UNINDENTED_CAUSED_BY)
    assert java_exc.exception_class == "Exception"
    assert java_exc.exception_message == "msg"
    assert java_exc.stack == ["at org.File.function(File.java:100)"]
    assert java_exc.additional == [
        "Caused by: Exception2: msg2; no stack trace available"
    ]


EXC_MSG_WITH_PARENS = """\
Exception: Error(

General Error: "No subscriptions created yet.")
\tat org.File.function(RustError.kt:4)
"""


def test_parenthesized_msg():
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
def test_malformed(text):
    with pytest.raises(libjava.MalformedJavaStackTrace):
        libjava.parse_java_stack_trace(text)
