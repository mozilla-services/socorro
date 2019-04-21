# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse

import mock
import pytest

from socorro.scripts import FallbackToPipeAction, FlagAction


class TestFlagAction:
    @pytest.mark.parametrize('args, expected', [
        # No args results in default
        ([], True),

        # Args result in appropriate values
        (['--flag'], True),
        (['--no-flag'], False),

        # Last arg wins
        (['--no-flag', '--flag'], True),
        (['--flag', '--no-flag'], False),
    ])
    def test_parsing(self, args, expected):
        parser = argparse.ArgumentParser()
        parser.add_argument('--flag', '--no-flag', dest='flag', default=True, action=FlagAction)

        args = parser.parse_args(args)
        assert args.flag is expected

    def test_value_error(self):
        """Validate flags--must have a flag and a no-flag"""
        parser = argparse.ArgumentParser()
        with pytest.raises(ValueError):
            # --flag and no --no-flag
            parser.add_argument('--flag', dest='flag', default=True, action=FlagAction)

        with pytest.raises(ValueError):
            # --no-flag and no --flag
            parser.add_argument('--no-flag', dest='flag', default=True, action=FlagAction)


class TestFallbackToPipeAction:
    def test_named_option_raises(self):
        """Init fails with positional args, since omitting skips the call."""
        parser = argparse.ArgumentParser()
        with pytest.raises(ValueError):
            parser.add_argument('--name', nargs='*',
                                action=FallbackToPipeAction)

    @pytest.mark.parametrize('nargs', ['?', '+', 1])
    def test_other_nargs_raises(self, nargs):
        """Init fails nargs!='*', since omitting skips the call."""
        parser = argparse.ArgumentParser()
        with pytest.raises(ValueError):
            parser.add_argument('name', nargs=nargs,
                                action=FallbackToPipeAction)

    def test_command_line(self):
        """Command line positional arguments are preferred."""
        parser = argparse.ArgumentParser()
        parser.add_argument('testid', nargs='*', action=FallbackToPipeAction)
        with mock.patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.side_effect = Exception('should not be called')
            args = parser.parse_args(['1', '2', '3'])
        assert args.testid == ['1', '2', '3']

    def test_stdin_fallback(self):
        """If positional arguments are omitted, the stdin is used."""
        parser = argparse.ArgumentParser()
        parser.add_argument('testid', nargs='*', action=FallbackToPipeAction)
        with mock.patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.__iter__.return_value = ['a\n', ' b\n', 'c\n']
            args = parser.parse_args([])
        assert args.testid == ['a', ' b', 'c']

    def test_stdin_tty_fails(self):
        """An interactive shell fails as a fallback."""
        parser = argparse.ArgumentParser()
        parser.add_argument('testid', nargs='*', action=FallbackToPipeAction)
        with mock.patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = True
            with pytest.raises(SystemExit):
                parser.parse_args([])

    def test_stdin_empty_fails(self):
        """An empty pipe fails as a fallback."""
        parser = argparse.ArgumentParser()
        parser.add_argument('testid', nargs='*', action=FallbackToPipeAction)
        with mock.patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = True
            mock_stdin.__iter__.return_value = []
            with pytest.raises(SystemExit):
                parser.parse_args([])

    def test_stdin_type_translation(self):
        """Values from stdin are processed by the type function."""
        parser = argparse.ArgumentParser()
        parser.add_argument('testid',
                            nargs='*',
                            type=int,
                            action=FallbackToPipeAction)
        with mock.patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.__iter__.return_value = ['1\n', '10\n', '1000\n']
            args = parser.parse_args([])
        assert args.testid == [1, 10, 1000]
