# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
from unittest import mock

import pytest

from socorro.scripts import FallbackToPipeAction, FlagAction


@pytest.fixture
def parser():
    return argparse.ArgumentParser()


@pytest.fixture
def fallback_parser(parser):
    parser.add_argument("testid", nargs="*", action=FallbackToPipeAction)
    return parser


@pytest.fixture
def mock_stdin():
    with mock.patch("sys.stdin", spec_set=["isatty", "__iter__"]) as mock_stdin:
        yield mock_stdin


class TestFlagAction:
    @pytest.mark.parametrize(
        "args, expected",
        [
            # No args results in default
            ([], True),
            # Args result in appropriate values
            (["--flag"], True),
            (["--no-flag"], False),
            # Last arg wins
            (["--no-flag", "--flag"], True),
            (["--flag", "--no-flag"], False),
        ],
    )
    def test_parsing(self, args, expected, parser):
        parser.add_argument(
            "--flag", "--no-flag", dest="flag", default=True, action=FlagAction
        )

        args = parser.parse_args(args)
        assert args.flag is expected

    def test_value_error(self, parser):
        """Validate flags--must have a flag and a no-flag"""
        with pytest.raises(ValueError):
            # --flag and no --no-flag
            parser.add_argument("--flag", dest="flag", default=True, action=FlagAction)

        with pytest.raises(ValueError):
            # --no-flag and no --flag
            parser.add_argument(
                "--no-flag", dest="flag", default=True, action=FlagAction
            )


class TestFallbackToPipeAction:
    def test_named_option_raises(self, parser):
        """Init fails with positional args, since omitting skips the call."""
        with pytest.raises(ValueError):
            parser.add_argument("--name", nargs="*", action=FallbackToPipeAction)

    @pytest.mark.parametrize("nargs", ["?", "+", 1])
    def test_other_nargs_raises(self, nargs, parser):
        """Init fails nargs!='*', since omitting skips the call."""
        with pytest.raises(ValueError):
            parser.add_argument("name", nargs=nargs, action=FallbackToPipeAction)

    def test_command_line(self, fallback_parser, mock_stdin):
        """Command line positional arguments are preferred."""
        mock_stdin.isatty.side_effect = Exception("should not be called")
        args = fallback_parser.parse_args(["1", "2", "3"])
        assert args.testid == ["1", "2", "3"]

    def test_stdin_fallback(self, fallback_parser, mock_stdin):
        """If positional arguments are omitted, the stdin is used."""
        mock_stdin.isatty.return_value = False
        mock_stdin.__iter__.return_value = ["a\n", " b\n", "c\n"]
        args = fallback_parser.parse_args([])
        assert args.testid == ["a", " b", "c"]

    def test_stdin_tty_fails(self, fallback_parser, mock_stdin):
        """An interactive shell fails as a fallback."""
        mock_stdin.isatty.return_value = True
        with pytest.raises(SystemExit):
            fallback_parser.parse_args([])

    def test_stdin_empty_fails(self, fallback_parser, mock_stdin):
        """An empty pipe fails as a fallback."""
        mock_stdin.isatty.return_value = True
        mock_stdin.__iter__.return_value = []
        with pytest.raises(SystemExit):
            fallback_parser.parse_args([])

    def test_stdin_type_translation(self, parser, mock_stdin):
        """Values from stdin are processed by the type function."""
        parser.add_argument("testid", nargs="*", type=int, action=FallbackToPipeAction)
        mock_stdin.isatty.return_value = False
        mock_stdin.__iter__.return_value = ["1\n", "10\n", "1000\n"]
        args = parser.parse_args([])
        assert args.testid == [1, 10, 1000]
