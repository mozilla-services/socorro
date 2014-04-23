from nose.tools import ok_

from crashstats.base import utils
from crashstats.base.tests.testbase import TestCase


class Tests(TestCase):

    def test_get_now(self):
        result = utils.get_now()
        ok_(result.tzinfo)  # timezone aware
