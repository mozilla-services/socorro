import urllib
import locale
from jingo import register


@register.filter
def split(value, separator):
    return value.split(separator)


@register.function
def truncatechars(str_, max_length):
    if len(str_) < max_length:
        return str_
    else:
        return '%s...' % str_[:max_length - len('...')]


@register.filter
def urlencode(txt):
    """Url encode a path."""
    # originally taken from funfactory but improved to support non-ascii
    # Unicode characters
    if isinstance(txt, unicode):
        txt = txt.encode('utf-8')
    return urllib.quote_plus(txt)


@register.filter
def digitgroupseparator(number):
    """AKA ``thousands separator'' - 1000000 becomes 1,000,000 """

    if type(number) is not int:
        return number

    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')

    return locale.format('%d', number, True)
