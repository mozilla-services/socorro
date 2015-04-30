"""
This is a "backport" from unittest2.

It's just a subset of the functionality of the whole of unittest2 but
it gives us the ability to set an *conditional* test case skip on a
whole class.
"""

import types
import functools


class SkipTest(Exception):
    pass


def _id(obj):  # identity function
    return obj


class_types = [type]
if getattr(types, 'ClassType', None):
    class_types.append(types.ClassType)
class_types = tuple(class_types)


def _skip(reason):
    """
    Unconditionally skip a test.
    """
    def decorator(test_item):
        if not isinstance(test_item, class_types):
            @functools.wraps(test_item)
            def skip_wrapper(*args, **kwargs):
                raise SkipTest(reason)
            test_item = skip_wrapper
        return SkipTest(reason)
    return decorator


def skip_if(condition, reason=''):
    """
    Decorator that works on classes and test methods and test functions.
    """
    if condition:
        return _skip(reason)
    else:
        return _id
