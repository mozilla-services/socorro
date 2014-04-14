from nose.tools import eq_
from django.test import TestCase


from crashstats.api.helpers import (
    pluralize
)


class TestPluralize(TestCase):

    def test_basics(self):
        eq_(pluralize(0), 's')
        eq_(pluralize(1), '')
        eq_(pluralize(59), 's')

    def test_overide_s(self):
        eq_(pluralize(59, 'ies'), 'ies')
