# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse

import pytest

from socorro.scripts import FlagAction


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
