# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from textwrap import dedent

import pytest

from crashstats.libbugzilla import (
    crash_report_to_description,
    minidump_thread_to_frames,
    truncate,
)


@pytest.mark.parametrize(
    "text, length, expected",
    [
        pytest.param("", 80, "", id="empty-string"),
        pytest.param("abc123", 80, "abc123", id="basic-string"),
        pytest.param("a" * 15, 10, ("a" * 7) + "...", id="truncated-string"),
    ],
)
def test_truncate(text, length, expected):
    assert truncate(text, length) == expected


@pytest.mark.parametrize(
    "thread, expected",
    [
        pytest.param(
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 1,
                    },
                ]
            },
            [
                {
                    "frame": 0,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:1",
                },
            ],
            id="everything_there",
        ),
        pytest.param(
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 0,
                    },
                    {
                        "frame": 1,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 1,
                    },
                    {
                        "frame": 2,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 2,
                    },
                    {
                        "frame": 3,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 3,
                    },
                    {
                        "frame": 4,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 4,
                    },
                    {
                        "frame": 5,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 5,
                    },
                    {
                        "frame": 6,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 6,
                    },
                    {
                        "frame": 7,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 7,
                    },
                    {
                        "frame": 8,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 8,
                    },
                    {
                        "frame": 9,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 9,
                    },
                    {
                        "frame": 10,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 10,
                    },
                    {
                        "frame": 11,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 11,
                    },
                ]
            },
            [
                {
                    "frame": 0,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:0",
                },
                {
                    "frame": 1,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:1",
                },
                {
                    "frame": 2,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:2",
                },
                {
                    "frame": 3,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:3",
                },
                {
                    "frame": 4,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:4",
                },
                {
                    "frame": 5,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:5",
                },
                {
                    "frame": 6,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:6",
                },
                {
                    "frame": 7,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:7",
                },
                {
                    "frame": 8,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:8",
                },
                {
                    "frame": 9,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:9",
                },
            ],
            id="more_than_ten_frames",
        ),
        pytest.param(
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": "fake_module",
                        "signature": "foo::bar(" + ("char* x, " * 15) + "int y)",
                        "file": "fake.cpp",
                        "line": 1,
                    },
                ]
            },
            [
                {
                    "frame": 0,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, char* x, char* x, char* x, char* x, char* x, char* x, char*...",
                    "source": "fake.cpp:1",
                },
            ],
            id="long_frame_signature",
        ),
        pytest.param(
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": 1,
                        "inlines": [
                            {
                                "file": "foo_inline.cpp",
                                "line": 100,
                                "function": "_foo_inline",
                            },
                            {
                                "file": "foo_inline.cpp",
                                "line": 4,
                                "function": "_foo_inline_amd64",
                            },
                        ],
                    },
                ]
            },
            [
                {
                    "frame": 0,
                    "module": "fake_module",
                    "signature": "_foo_inline",
                    "source": "foo_inline.cpp:100",
                },
                {
                    "frame": 0,
                    "module": "fake_module",
                    "signature": "_foo_inline_amd64",
                    "source": "foo_inline.cpp:4",
                },
                {
                    "frame": 0,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp:1",
                },
            ],
            id="inline_functions",
        ),
        pytest.param(
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": None,
                        "signature": "(unloaded unmod@0xe4df)",
                        "file": None,
                        "line": None,
                    },
                ]
            },
            [
                {
                    "frame": 0,
                    "module": "?",
                    "signature": "(unloaded unmod@0xe4df)",
                    "source": "",
                },
            ],
            id="unloaded_module",
        ),
        pytest.param(
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": "fake.cpp",
                        "line": None,
                    },
                ]
            },
            [
                {
                    "frame": 0,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "fake.cpp",
                },
            ],
            id="missing_lineno",
        ),
        pytest.param(
            {
                "frames": [
                    {
                        "frame": 0,
                        "module": "fake_module",
                        "signature": "foo::bar(char* x, int y)",
                        "file": None,
                        "line": 1,
                    },
                ]
            },
            [
                {
                    "frame": 0,
                    "module": "fake_module",
                    "signature": "foo::bar(char* x, int y)",
                    "source": "",
                },
            ],
            id="missing_file",
        ),
    ],
)
def test_minidump_thread_to_frames(thread, expected):
    assert minidump_thread_to_frames(thread) == expected


class Testcrash_report_to_description:
    URL = "http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401"

    def test_comment(self):
        processed_crash = {
            "reason": "SIGSEGV /0x00000080",
            "crashing_thread": 0,
            "json_dump": {
                "threads": [
                    {
                        "frames": [
                            {
                                "frame": 0,
                                "module": "fake_module",
                                "signature": "foo::bar(char* x, int y)",
                                "file": "fake.cpp",
                                "line": 1,
                            },
                        ],
                    }
                ],
            },
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            Reason: ```SIGSEGV /0x00000080```

            Top 1 frame:
            ```
            0  fake_module  foo::bar(char* x, int y)  fake.cpp:1
            ```"""
        )

    def test_comment_no_data(self):
        processed_crash = {}
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            No stack."""
        )

    def test_comment_no_frame_data(self):
        """If a frame is missing everything, do not throw an error."""
        processed_crash = {
            "crashing_thread": 0,
            "json_dump": {
                "threads": [
                    {
                        "frames": [
                            {},
                        ],
                    }
                ],
            },
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        # NOTE(willkg): This is a silly looking stack, but the important part here is
        # that it produces something and doesn't throw an error
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            Top 1 frame:
            ```
            ?  ?
            ```"""
        )

    def test_comment_reason(self):
        """Verify Reason makes it into the comment."""
        processed_crash = {
            "reason": "SIGSEGV /0x00000080",
            "crashing_thread": 0,
            "json_dump": {
                "threads": [
                    {
                        "frames": [
                            {
                                "frame": 0,
                                "module": "fake_module",
                                "signature": "foo::bar(char* x, int y)",
                                "file": "fake.cpp",
                                "line": 1,
                            },
                        ],
                    }
                ],
            },
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            Reason: ```SIGSEGV /0x00000080```

            Top 1 frame:
            ```
            0  fake_module  foo::bar(char* x, int y)  fake.cpp:1
            ```"""
        )

    def test_comment_moz_crash_reason(self):
        """Verify moz_crash_reason makes it into comment--but not moz_crash_reason_raw."""
        processed_crash = {
            "moz_crash_reason": "good data",
            "moz_crash_reason_raw": "bad data",
            "crashing_thread": 0,
            "json_dump": {
                "threads": [
                    {
                        "frames": [
                            {
                                "frame": 0,
                                "module": "fake_module",
                                "signature": "foo::bar(char* x, int y)",
                                "file": "fake.cpp",
                                "line": 1,
                            },
                        ],
                    }
                ],
            },
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            MOZ_CRASH Reason: ```good data```

            Top 1 frame:
            ```
            0  fake_module  foo::bar(char* x, int y)  fake.cpp:1
            ```"""
        )

    def test_comment_moz_crash_reason_upstages_reason(self):
        """Verify moz_crash_reason shows up but not reason when they're both there."""
        processed_crash = {
            "reason": "EXCEPTION_BREAKPOINT",
            "moz_crash_reason": "MOZ_CRASH(Quota manager shutdown timed out) (good)",
            "moz_crash_reason_raw": "MOZ_CRASH(Quota manager shutdown timed out) (bad)",
            "crashing_thread": 0,
            "json_dump": {
                "threads": [
                    {
                        "frames": [
                            {
                                "frame": 0,
                                "module": "fake_module",
                                "signature": "foo::bar(char* x, int y)",
                                "file": "fake.cpp",
                                "line": 1,
                            },
                        ],
                    }
                ],
            },
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            MOZ_CRASH Reason: ```MOZ_CRASH(Quota manager shutdown timed out) (good)```

            Top 1 frame:
            ```
            0  fake_module  foo::bar(char* x, int y)  fake.cpp:1
            ```"""
        )

    def test_comment_crashing_thread_none(self):
        """Verify no crashing thread is treated as thread 0 with note."""
        processed_crash = {
            "json_dump": {
                "threads": [
                    {
                        "frames": [
                            {
                                "frame": 0,
                                "module": "fake_module",
                                "signature": "foo::bar(char* x, int y)",
                                "file": "fake.cpp",
                                "line": 1,
                            },
                        ],
                    }
                ],
            },
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            No crashing thread identified; using thread 0.

            Top 1 frame:
            ```
            0  fake_module  foo::bar(char* x, int y)  fake.cpp:1
            ```"""
        )

    def test_comment_java_stack_trace(self):
        """If there's a java stack trace, use that instead

        Also verify tabs get converted to 4-spaces.

        """
        processed_crash = {
            "java_stack_trace": dedent(
                """\
                java.lang.NoClassDefFoundError: kotlinx.coroutines.channels.BufferedChannel
                \tat kotlinx.coroutines.channels.ChannelKt.Channel$default(Channel.kt:44)
                \tat androidx.datastore.core.SimpleActor.<init>(SimpleActor.kt:18)
                \tat androidx.datastore.core.SingleProcessDataStore.<init>(SingleProcessDataStore.kt:68)
                \tat androidx.datastore.DataStoreSingletonDelegate.getValue(DataStoreDelegate.kt:81)"""
            )
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            Java stack trace:
            ```
            java.lang.NoClassDefFoundError: kotlinx.coroutines.channels.BufferedChannel
                at kotlinx.coroutines.channels.ChannelKt.Channel$default(Channel.kt:44)
                at androidx.datastore.core.SimpleActor.<init>(SimpleActor.kt:18)
                at androidx.datastore.core.SingleProcessDataStore.<init>(SingleProcessDataStore.kt:68)
                at androidx.datastore.DataStoreSingletonDelegate.getValue(DataStoreDelegate.kt:81)
            ```"""
        )

    def test_comment_java_exception(self):
        """If there's a java_exception, use that."""
        processed_crash = {
            "java_exception": {
                "exception": {
                    "values": [
                        {
                            "stacktrace": {
                                "frames": [
                                    {
                                        "module": "kotlinx.coroutines.channels.ChannelKt",
                                        "function": "Channel$default",
                                        "in_app": True,
                                        "lineno": 44,
                                        "filename": "Channel.kt",
                                    },
                                    {
                                        "module": "androidx.datastore.core.SimpleActor",
                                        "function": "<init>",
                                        "in_app": True,
                                        "lineno": 18,
                                        "filename": "SimpleActor.kt",
                                    },
                                ]
                            }
                        }
                    ]
                }
            }
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            Top 2 frames:
            ```
            0  kotlinx.coroutines.channels.ChannelKt  Channel$default  Channel.kt:44
            1  androidx.datastore.core.SimpleActor  <init>  SimpleActor.kt:18
            ```"""
        )

    def test_comment_java_exception_upstages_java_stack_trace(self):
        """Use java_exception instead of java_stack_trace."""
        processed_crash = {
            "java_stack_trace": dedent(
                """\
                java.lang.NoClassDefFoundError: kotlinx.coroutines.channels.BufferedChannel
                \tat kotlinx.coroutines.channels.ChannelKt.Channel$default(Channel.kt:44)
                \tat androidx.datastore.core.SimpleActor.<init>(SimpleActor.kt:18)
                \tat androidx.datastore.core.SingleProcessDataStore.<init>(SingleProcessDataStore.kt:68)
                \tat androidx.datastore.DataStoreSingletonDelegate.getValue(DataStoreDelegate.kt:81)"""
            ),
            "java_exception": {
                "exception": {
                    "values": [
                        {
                            "stacktrace": {
                                "frames": [
                                    {
                                        "module": "kotlinx.coroutines.channels.ChannelKt",
                                        "function": "Channel$default",
                                        "in_app": True,
                                        "lineno": 44,
                                        "filename": "Channel.kt",
                                    },
                                    {
                                        "module": "androidx.datastore.core.SimpleActor",
                                        "function": "<init>",
                                        "in_app": True,
                                        "lineno": 18,
                                        "filename": "SimpleActor.kt",
                                    },
                                ]
                            }
                        }
                    ]
                }
            },
        }
        comment = crash_report_to_description(self.URL, processed_crash)
        assert comment == dedent(
            """\
            Crash report: http://localhost:8000/report/index/2ae0a833-f43d-4d9b-8c13-f99e70240401

            Top 2 frames:
            ```
            0  kotlinx.coroutines.channels.ChannelKt  Channel$default  Channel.kt:44
            1  androidx.datastore.core.SimpleActor  <init>  SimpleActor.kt:18
            ```"""
        )
