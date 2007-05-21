"""
Helper functions

All names available in this module will be available under the Pylons h object.
"""
from webhelpers import *
from pylons.helpers import log
from pylons.i18n import get_lang, set_lang

from genshi.core import Markup
def wrap_helpers(localdict):
    def helper_wrapper(func):
        def wrapped_helper(*args, **kw):
            return Markup(func(*args, **kw))
        wrapped_helper.__name__ = func.__name__
        return wrapped_helper
    for name, func in localdict.iteritems():
        if not callable(func) or not func.__module__.startswith('webhelpers.rails'):
            continue
        localdict[name] = helper_wrapper(func)
wrap_helpers(locals())

def EmptyFilter(x):
  """Return None if the argument is an empty string, otherwise
     return the argument."""
  if x == '':
    return None
  return x
