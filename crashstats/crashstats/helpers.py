from jingo import register


@register.filter
def split(value, separator):
    return value.split(separator)
