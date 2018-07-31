from functools import total_ordering


@total_ordering
class EqualAnything(object):
    def __eq__(self, other):
        return True

    def __lt__(self, other):
        return True


#: Sentinel that is equal to anything; simplifies assertions in cases where
#: part of the value changes from test to test
WHATEVER = EqualAnything()
