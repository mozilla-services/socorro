# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import unittest

from socorro.cron.base import SubprocessMixin


_SCRIPT = os.path.join(os.path.dirname(__file__), 'sampleapp.py')


class TestSubprocessMixin(unittest.TestCase, SubprocessMixin):

    def test_clean_no_errors(self):
        exit_code, stdout, stderr = self.run_process(
            [_SCRIPT]
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')

    def test_failing_one_error(self):
        exit_code, stdout, stderr = self.run_process(
            [_SCRIPT, '--exit', 1, '-e', 'Error']
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, 'Error')

    def test_clean_some_output(self):
        exit_code, stdout, stderr = self.run_process(
            [_SCRIPT, '-o', 'Blather']
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, 'Blather')
        self.assertEqual(stderr, '')

    def test_as_command_string(self):
        exit_code, stdout, stderr = self.run_process(
            '%s --exit=9 -o Blather -e Error' % _SCRIPT
        )
        self.assertEqual(exit_code, 9)
        self.assertEqual(stdout, 'Blather')
        self.assertEqual(stderr, 'Error')
