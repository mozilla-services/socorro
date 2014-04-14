# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import unittest

from nose.tools import eq_

from socorro.cron.mixins import with_subprocess


_SCRIPT = os.path.join(os.path.dirname(__file__), 'sampleapp.py')

@with_subprocess
class TestSubprocessMixin(unittest.TestCase):

    def test_clean_no_errors(self):
        exit_code, stdout, stderr = self.run_process(
            [_SCRIPT]
        )
        eq_(exit_code, 0)
        eq_(stdout, '')
        eq_(stderr, '')

    def test_failing_one_error(self):
        exit_code, stdout, stderr = self.run_process(
            [_SCRIPT, '--exit', 1, '-e', 'Error']
        )
        eq_(exit_code, 1)
        eq_(stdout, '')
        eq_(stderr, 'Error')

    def test_clean_some_output(self):
        exit_code, stdout, stderr = self.run_process(
            [_SCRIPT, '-o', 'Blather']
        )
        eq_(exit_code, 0)
        eq_(stdout, 'Blather')
        eq_(stderr, '')

    def test_as_command_string(self):
        exit_code, stdout, stderr = self.run_process(
            '%s --exit=9 -o Blather -e Error' % _SCRIPT
        )
        eq_(exit_code, 9)
        eq_(stdout, 'Blather')
        eq_(stderr, 'Error')
