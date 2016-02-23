import urllib
import warnings
import datetime

from django_jinja import library
import jinja2

from django.forms.widgets import RadioSelect


@library.global_function
def describe_friendly_type(type_):
    if type_ is basestring:
        return "String"
    if type_ is int:
        return "Integer"
    if type_ is list:
        return "List of strings"
    if type_ is datetime.date:
        return "Date"
    if type_ is datetime.datetime:
        return "Date and time"
    if type_ is bool:
        return "Boolean"
    warnings.warn("Don't know how to describe type %r" % type_)
    return type_


@library.global_function
def make_test_input(parameter, defaults):
    if parameter['type'] is bool:
        # If it's optional, make it possible to select "Not set",
        if parameter['required']:
            raise NotImplementedError(
                'required booleans are not supported'
            )
        else:
            widget = RadioSelect(choices=(
                ('', 'Not set'),
                ('false', 'False'),
                ('true', 'True'),
            ))
            return widget.render(parameter['name'], '')

    template = u'<input type="%(type)s" name="%(name)s"'
    data = {
        'name': parameter['name'],
    }
    classes = []
    if parameter['required']:
        classes.append('required')

    if parameter['type'] is datetime.date:
        data['type'] = 'date'
    else:
        data['type'] = 'text'
    if parameter['type'] is not basestring:
        classes.append('validate-%s' % parameter['type'].__name__)
    if defaults.get(parameter['name']):
        data['value'] = urllib.quote(unicode(defaults.get(parameter['name'])))
    else:
        data['value'] = ''

    data['classes'] = ' '.join(classes)
    if data['classes']:
        template += ' class="%(classes)s"'
    if data['value']:
        template += ' value="%(value)s"'
    template += '>'
    html = template % data
    return jinja2.Markup(html)


@library.filter
def pluralize(count, multiple='s', single=''):
    if count == 1:
        return single
    return multiple
