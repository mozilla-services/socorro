from nose.tools import eq_

from crashstats.base.tests.testbase import TestCase
from crashstats.base.utils import render_exception


class TestRenderException(TestCase):

    def test_basic(self):
        html = render_exception('hi!')
        eq_(html, '<ul><li>hi!</li></ul>')

    def test_escaped(self):
        html = render_exception('<hi>')
        eq_(html, '<ul><li>&lt;hi&gt;</li></ul>')

    def test_to_string(self):
        try:
            raise NameError('<hack>')
        except NameError as exc:
            html = render_exception(exc)
        eq_(html, '<ul><li>&lt;hack&gt;</li></ul>')
