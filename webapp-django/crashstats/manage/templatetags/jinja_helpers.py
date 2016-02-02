from django_jinja import library


@library.filter
def show_percentage(value):
    if value == int(value):  # a whole number like 10.0
        return '%d%%' % value
    return "%.1f%%" % value


@library.filter
def msec2sec(value):
    return '%.2f' % (value / 1000.0)
