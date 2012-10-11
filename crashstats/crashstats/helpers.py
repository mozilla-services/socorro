import urllib
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
