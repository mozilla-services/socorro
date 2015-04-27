from socorro.unittest.testbase import TestCase
from socorro.unittest import skip_if


@skip_if(True, 'Impossible!')
class TestDivisionByZero(TestCase):

    def test_insanity(self):
        assert 1 / 0 == 42


@skip_if(False)
class TestDivisionByOne(TestCase):

    def test_sanity(self):
        assert 1 / 1 == 1

    @skip_if(True, 'Not a good idea')
    def test_insanity(self):
        assert 1 / 0 == 42


@skip_if(False)
def test_one():
    assert 1


@skip_if(True)
def test_zero():
    assert 0
