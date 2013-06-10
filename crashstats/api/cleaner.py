import warnings

from crashstats import scrubber


class Cleaner(object):
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

    ANY = '__any__'

    def __init__(self, whitelist, clean_scrub=None, debug=False):
        self.whitelist = whitelist
        self.clean_scrub = clean_scrub
        self.debug = debug

    def start(self, data):
        self._scrub(data, self.whitelist)

    def _scrub(self, result, api_whitelist):
        if isinstance(api_whitelist, (list, tuple)):
            if isinstance(result, dict):
                self._scrub_item(result, api_whitelist)
            else:
                self._scrub_list(result, api_whitelist)
        else:
            for result_key, whitelist in api_whitelist.items():
                if result_key == self.ANY:
                    if isinstance(whitelist, (list, tuple)):
                        if isinstance(result, dict):
                            for key, thing in result.iteritems():
                                if isinstance(thing, dict):
                                    self._scrub_item(thing, whitelist)
                                elif isinstance(thing, (list, tuple)):
                                    self._scrub_list(thing, whitelist)

                    else:
                        for datum in result.values():
                            self._scrub(datum, whitelist)
                else:
                    data = result[result_key]
                    if isinstance(data, dict):
                        self._scrub(data, whitelist)
                    elif isinstance(data, list):
                        self._scrub_list(data, whitelist)

    def _scrub_item(self, data, whitelist):
        for key in data.keys():
            if key not in whitelist:
                # warnings.warn() never redirects the same message to
                # the logger more than once in the same python
                # process. Doing this helps developers notice/remember
                # which fields are being left out
                if self.debug:
                    msg = 'Skipping %r' % (key,)
                    warnings.warn(msg)
                del data[key]

        if self.clean_scrub:
            scrubber.scrub_dict(
                data,
                clean_fields=self.clean_scrub,
            )

    def _scrub_list(self, sequence, whitelist):
        for i, data in enumerate(sequence):
            self._scrub_item(data, whitelist)
            sequence[i] = data
