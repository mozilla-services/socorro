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
