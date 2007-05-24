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

def url_quote(s):
  """
  Utility function to properly encode "+" characters that are often found
  in signatures.  Without this, they get automatically converted into
  spaces by python and we never get any results from the the reports
  controller.  Cast it to str since it could be None|'' and we don't want 
  urllib.quote to get angry.
  """
  from urllib import quote
  return quote(str(s))

def url_unquote(s):
  """
  Function to properly dencode special urls before passing to url_for.  Used in
  conjunction with url_quote for "+" characters.
  """
  from urllib import unquote
  return unquote(str(s))

def get_row_class(i):
  """
  Return a row class (1|2) based on passed value.  For use in alternating table
  row colors.
  """
  return 'row'+str(int(i)%2+1)
