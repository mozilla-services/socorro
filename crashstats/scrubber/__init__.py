# coding=utf-8

import re


# source: http://stackp.online.fr/?p=19
EMAIL = re.compile('([\w\-\.]+@(\w[\w\-]+\.)+[\w\-]+)')


# source: http://stackoverflow.com/questions/520031
URL = re.compile(
    r"((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.‌​]"
    "[a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))*))+(?:(([^\s()<>]"
    "+|(‌​([^\s()<>]+)))*)|[^\s`!()[]{};:'\".,<>?«»“”‘’]))",
    re.DOTALL
)


def scrub_data(data, **kwargs):
    """Return a scrubbed copy of a list of dictionaries.

    See `scrub_dict` for parameters.
    """
    scrubbed = list(data)
    for i, item in enumerate(scrubbed):
        scrubbed[i] = scrub_dict(item, **kwargs)
    return scrubbed


def scrub_dict(
    data,
    remove_fields=None,
    replace_fields=None,
    clean_fields=None,
    make_copy=False
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
        * example: replace_fields=[('email', 'scrubbed email'), ('phone', '')]
    * clean_fields
        * list or tuple of 2-uples
        * search for patterns in those fields and remove what matches
        * example: clean_fields=[('comment', EMAIL), ('comment', URL)]

    Any number of those options can be used in the same call. If none is used,
    return the dictionary unchanged.
    """
    if make_copy:
        scrubbed = data.copy()
    else:
        scrubbed = data
    for key in remove_fields or []:
        if key in scrubbed:
            del scrubbed[key]

    for key in scrubbed:
        for field in replace_fields or []:
            if field[0] == key:
                scrubbed[key] = field[1]

        for field in clean_fields or []:
            if field[0] == key and scrubbed[key]:
                scrubbed[key] = scrub_string(scrubbed[key], field[1])

    return scrubbed


def scrub_string(data, pattern, replace_with=''):
    """Return a copy of a string where everything that matches the pattern is
    removed.
    """
    for i in pattern.findall(data):
        data = data.replace(i[0], replace_with)
    return data
