# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import warnings


class Cleaner:
    """
    This class takes care of cleaning up a chunk of data that is some sort of
    mix of dicts and lists and stuff. The simplest case is::

        >>> data = {"hits": [{"foo": 1, "bar": 2}, {"foo": 3, "bar": 4}]}

    Then if you use::

        >>> c = Cleaner({'hits': ('foo',)})
        >>> c.start(data)
        >>> print data
        {"hits": [{"foo": 1}, {"foo": 3}]}

    Note, it removed the key `bar` for each dict under `data['hits']`.

    A more complex example is when the keys in dicts aren't predictable:

        >>> data = {"Firefox": [{"foo": 1, "bar": 2}, {"foo": 3, "bar": 4}],
        ...         "TB": [{"foo": 5, "bar": 6}, {"foo": 7, "bar": 8}]}
        >>> c = Cleaner({Cleaner.ANY: ('foo',)})
        >>> c.start(data)
        >>> print data
        {"Firefox": [{"foo": 1}, {"foo": 3}], "TB": [{"foo": 5}, {"foo": 7}]}

    """

    ANY = "__any__"

    def __init__(self, allowlist, debug=False):
        self.allowlist = allowlist
        self.debug = debug

    def start(self, data):
        self._scrub(data, self.allowlist)

    def _scrub(self, result, api_allowlist):
        if isinstance(api_allowlist, (list, tuple)):
            if isinstance(result, dict):
                self._scrub_item(result, api_allowlist)
            else:
                self._scrub_list(result, api_allowlist)
        else:
            for result_key, allowlist in api_allowlist.items():
                if result_key == self.ANY:
                    if isinstance(allowlist, (list, tuple)):
                        if isinstance(result, dict):
                            for key, thing in result.items():
                                if isinstance(thing, dict):
                                    self._scrub_item(thing, allowlist)
                                elif isinstance(thing, (list, tuple)):
                                    self._scrub_list(thing, allowlist)

                    else:
                        for datum in result.values():
                            self._scrub(datum, allowlist)
                else:
                    data = result[result_key]
                    if isinstance(data, dict):
                        self._scrub(data, allowlist)
                    elif isinstance(data, list):
                        self._scrub_list(data, allowlist)

    def _scrub_item(self, data, allowlist):
        matcher = SmartAllowlistMatcher(allowlist)
        for key in list(data.keys()):
            if key not in matcher:
                # warnings.warn() never redirects the same message to
                # the logger more than once in the same python
                # process. Doing this helps developers notice/remember
                # which fields are being left out
                if self.debug:
                    msg = "Skipping %r" % (key,)
                    warnings.warn(msg)
                del data[key]

    def _scrub_list(self, sequence, allowlist):
        for i, data in enumerate(sequence):
            self._scrub_item(data, allowlist)
            sequence[i] = data


class SmartAllowlistMatcher:
    def __init__(self, allowlist):
        def format(item):
            return "^" + item.replace("*", r"[\w-]*") + "$"

        items = [format(x) for x in allowlist]
        self.regex = re.compile("|".join(items))

    def __contains__(self, key):
        return bool(self.regex.match(key))
