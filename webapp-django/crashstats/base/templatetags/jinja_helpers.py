import urlparse
import urllib

import jinja2
from django_jinja import library

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.urlresolvers import reverse

from crashstats.base.utils import urlencode_obj


@library.global_function
def url(viewname, *args, **kwargs):
    """Makes it possible to construct URLs from templates.

    Because this function is used by taking user input, (e.g. query
    string values), we have to sanitize the values.
    """
    def clean_argument(s):
        if isinstance(s, basestring):
            # First remove all proper control characters like '\n',
            # '\r' or '\t'.
            s = ''.join(c for c in s if ord(c) >= 32)
            # Then, if any '\' left (it might have started as '\\nn')
            # remove those too.
            while '\\' in s:
                s = s.replace('\\', '')
            return s
        return s

    args = [clean_argument(x) for x in args]
    kwargs = dict((x, clean_argument(y)) for x, y in kwargs.items())

    return reverse(viewname, args=args, kwargs=kwargs)


@library.global_function
def static(path):
    return staticfiles_storage.url(path)


@library.global_function
@jinja2.contextfunction
def change_query_string(context, **kwargs):
    """
    Template function for modifying the current URL by parameters.
    You use it like this in a template:

        <a href={{ change_query_string(foo='bar') }}>

    And it takes the current request's URL (and query string) and modifies it
    just by the parameters you pass in. So if the current URL is
    `/page/?day=1` the output of this will become:

        <a href=/page?day=1&foo=bar>

    You can also pass lists like this:

        <a href={{ change_query_string(thing=['bar','foo']) }}>

    And you get this output:

        <a href=/page?day=1&thing=bar&thing=foo>

    And if you want to remove a parameter you can explicitely pass it `None`.
    Like this for example:

        <a href={{ change_query_string(day=None) }}>

    And you get this output:

        <a href=/page>

    """
    if kwargs.get('_no_base'):
        kwargs.pop('_no_base')
        base = ''
    else:
        base = context['request'].META['PATH_INFO']
    qs = urlparse.parse_qs(context['request'].META['QUERY_STRING'])
    for key, value in kwargs.items():
        if value is None:
            # delete the parameter
            if key in qs:
                del qs[key]
        else:
            # change it
            qs[key] = value
    new_qs = urllib.urlencode(qs, True)

    # We don't like + as the encoding character for spaces. %20 is better.
    new_qs = new_qs.replace('+', '%20')
    if new_qs:
        return '%s?%s' % (base, new_qs)
    return base


@library.global_function
def make_query_string(**kwargs):
    return urlencode_obj(kwargs)


@library.global_function
def is_dangerous_cpu(cpu_info):
    # These models are known to cause lots of crashes, we want to mark them
    # for ease of find by users.
    return (
        cpu_info.startswith('AuthenticAMD family 20 model 1') or
        cpu_info.startswith('AuthenticAMD family 20 model 2')
    )
