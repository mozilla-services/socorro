import urllib
from jingo import register


@register.filter
def split(value, separator):
    return value.split(separator)


@register.function
def urlquote(value):
    return urllib.quote(value)
