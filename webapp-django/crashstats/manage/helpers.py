from jingo import register


@register.filter
def show_percentage(value):
    if value == int(value):  # a whole number like 10.0
        return '%d%%' % value
    return "%.1f%%" % value
