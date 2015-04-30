# coding=utf-8

import re
import json
import warnings

from configman import RequiredConfig, Namespace

# source: http://stackp.online.fr/?p=19
EMAIL = re.compile('([\w\-\.]+@(\w[\w\-]+\.)+[\w\-]+)')


# source: http://stackoverflow.com/questions/520031
URL = re.compile(
    r"((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.‌​]"
    "[a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))*))+(?:(([^\s()<>]"
    "+|(‌​([^\s()<>]+)))*)|[^\s`!()[]{};:'\".,<>?«»“”‘’]))",
    re.DOTALL
)


# =============================================================================
class Cleaner(RequiredConfig):
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
    required_config = Namespace()
    required_config.add_option(
        'whitelist',
        default=None,
        doc='a list or dict in json form',
        from_string_converter=json.loads
    )
    required_config.add_option(
        'clean_scrub',
        default=None,
        doc='a list or dict in json form',
        from_string_converter=json.loads
    )
    required_config.add_option(
        'debug',
        default=False,
        doc='include debug information',
    )

    ANY = '__any__'

    def __init__(self, config):
        self.config = config
        self.whitelist = config.whitelist
        self.clean_scrub = config.clean_scrub
        self.debug = config.debug

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
        matcher = SmartWhitelistMatcher(whitelist)
        for key in data.keys():
            if key not in matcher:
                # warnings.warn() never redirects the same message to
                # the logger more than once in the same python
                # process. Doing this helps developers notice/remember
                # which fields are being left out
                if self.debug:
                    msg = 'Skipping %r' % (key,)
                    warnings.warn(msg)
                del data[key]

        if self.clean_scrub:
            self._scrub_dict(
                data,
                clean_fields=self.clean_scrub,
            )

    def _scrub_list(self, sequence, whitelist):
        for i, data in enumerate(sequence):
            self._scrub_item(data, whitelist)
            sequence[i] = data

    def _scrub_string(self, data, pattern, replace_with=''):
        """Return a copy of a string where everything that matches the pattern
        is removed.
        """
        for i in pattern.findall(data):
            data = data.replace(i[0], replace_with)
        return data

    def _scrub_dict(
        self,
        data,
        # remove_fields=None,
        replace_fields=None,
        clean_fields=None,
    ):
        """Edit a dictionary in place (or make and return a copy if passed the
        ``make_copy=True`` parameters).

        Several options are available:
        * remove_fields
            * list or tuple of strings
            * remove those fields from the dictionary
            * example: remove_fields=['email', 'phone']
        * replace_fields
            * list or tuple of 2-uples
            * replace the value of those fields with some content
            * example: replace_fields= \
                [('email', 'scrubbed email'), ('phone', '')]
        * clean_fields
            * list or tuple of 2-uples
            * search for patterns in those fields and remove what matches
            * example: clean_fields=[('comment', EMAIL), ('comment', URL)]

        Any number of those options can be used in the same call. If none is
        used, return the dictionary unchanged.
        """
        # data = data
        # for key in remove_fields or []:
        #     if key in data:
        #         del data[key]

        for key in data:
            # for field in replace_fields or []:
            #     if field[0] == key:
            #         data[key] = field[1]

            for field in clean_fields or []:
                if field[0] == key and data[key]:
                    data[key] = self._scrub_string(data[key], field[1])


# =============================================================================
class SmartWhitelistMatcher(object):

    def __init__(self, whitelist):

        def format(item):
            return '^' + item.replace('*', '[\w-]*') + '$'

        items = [format(x) for x in whitelist]
        self.regex = re.compile('|'.join(items))

    def __contains__(self, key):
        return bool(self.regex.match(key))
