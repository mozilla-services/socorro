import unittest

from nose.tools import ok_

from crashstats.base import utils


class Tests(unittest.TestCase):

    def test_get_now(self):
        result = utils.get_now()
        ok_(result.tzinfo)  # timezone aware
