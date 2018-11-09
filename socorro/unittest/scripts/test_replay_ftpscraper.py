# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from socorro.scripts.replay_ftpscraper import main
from socorro.unittest.scripts import with_scriptname


def test_missing_args(capsys):
    with with_scriptname('replay_ftpscraper'):
        # Make sure that running main with no args causes the script to exit with exit_code 2
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.exconly() == 'SystemExit: 2'

        # Make sure it prints some stuff to stdout
        out, err = capsys.readouterr()
        python2_usage_text = (
            'usage: replay_ftpscraper [-h] ftpscraperlog\n'
            'replay_ftpscraper: error: too few arguments\n'
        )
        python3_usage_text = (
            'usage: replay_ftpscraper [-h] ftpscraperlog\n'
            'replay_ftpscraper: error: the following arguments are required: ftpscraperlog\n'
        )
        assert err in [python2_usage_text, python3_usage_text]


def test_bad_file(capsys):
    with with_scriptname('replay_ftpscraper'):
        exit_code = main(['foo.txt'])
        assert exit_code == 1

        out, err = capsys.readouterr()
        usage_text = 'ftpscraper log "foo.txt" does not exist. Exiting.\n'
        assert out == usage_text
