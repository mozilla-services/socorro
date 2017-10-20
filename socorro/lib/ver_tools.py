# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""A function and supporting structure to turn Mozilla version strings into
a sortable normalized format.

Pubic Functions:

normalize - given a version in a string, this function returns a list of
            normalized version parts of the abcd format outlined in
            https://developer.mozilla.org/en/Toolkit_version_format
            Two lists are comparable using standard relational operators:
            <,>,!=,==, etc.

"""

import re


# got a better memoizer?  feel free to replace...
def _memoize_args_only(max_cache_size=1000):
    """Python 2.4 compatible memoize decorator.
    It creates a cache that has a maximum size.  If the cache exceeds the max,
    it is thrown out and a new one made.  With such behavior, it is wise to set
    the cache just a little larger that the maximum expected need.

    Parameters:
      max_cache_size - the size to which a cache can grow

    Limitations:
      The cache works only on args, not kwargs
    """
    def wrapper(f):
        def fn(*args):
            try:
                return fn.cache[args]
            except KeyError:
                if fn.count >= max_cache_size:
                    fn.cache = {}
                    fn.count = 0
                fn.cache[args] = result = f(*args)
                fn.count += 1
                return result
        fn.cache = {}
        fn.count = 0
        return fn
    return wrapper


# to allow for easy replacement of the memoize decorator used below
memoize = _memoize_args_only

# a regular expression to match the 'abcd' format defined in
# https://developer.mozilla.org/en/Toolkit_version_format
_version_part_re = re.compile("(\d*)([a-zA-Z]*)(\d*)([a-zA-Z]*)$")

# the alphabetic parts of a version string should sort to the high end if
# missing.  This allows version '3.6' to sort as greater than '3.6b1'
# set to a high value greater than any expected string fragment to
# be found in a real version string
_padding_high_string = 'zzzzzz'

# Mozilla versions consist of repeating 4-tuples in the pattern of
# int, string, int, string.  Because the output of the normalize
# function is a list and lists when compared for equailty must be of the
# same length, this list is used as an extension to any normalized
# version lists that are shorter than a standard.  See the max_version_parts
# parameter of the normalize function for the length.
_padding_list = [0, _padding_high_string, 0, _padding_high_string]


# Conversion of the 4-tuples to numeric or lexically comparable values
# are handled with some helper functions.  Missing numbers are to sort
# low, while missing strings are to sort high.
def _str_to_int(x):
    """given a string, this function converts to an int"""
    if x is None or x == '':
        return 0
    return int(x)


def _str_to_high_str(x):
    """given a string, this funtion converts the special values '' and None
    to the special value 'zzzzzz'.  This is used to insure empty values have
    a high sort order"""
    if x is None or x == '':
        return _padding_high_string
    return x


# corresponding to the int, string, int, string pattern of the 4-tuple
# this tuple allows the groups found by a regular expression to be
# conveniently converted.
_normalize_fn_list = (_str_to_int, _str_to_high_str,
                      _str_to_int, _str_to_high_str)


class NotAVersionException(Exception):
    """An exception raised by the class VersionComparer if given a string
    outside the standards of a version string as specified by the regular
    expression _version_part_re"""
    pass


@memoize(1000)
def normalize(version_string, max_version_parts=4):
    """turn a string representing a version into a normalized version list.
    Version lists are directly comparable using standard operators such as
    >, <, ==, etc.

    Parameters:
      version_string - such as '3.5' or '3.6.3plugin3'
      max_version_parts - version strings are comprised of a series of 4 tuples.
                          This should be set to the maximum number of 4 tuples
                          in a version string.
    """
    version_list = []
    for part_count, version_part in enumerate(version_string.split('.')):
        try:
            groups = _version_part_re.match(version_part).groups()
        except Exception:
            raise NotAVersionException(version_string)
        version_list.extend(t(x) for x, t in zip(groups, _normalize_fn_list))
    version_list.extend(_padding_list * (max_version_parts - part_count - 1))
    return version_list
