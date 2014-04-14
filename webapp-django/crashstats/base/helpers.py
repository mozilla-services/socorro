import cgi
import urllib

import jinja2
from jingo import register


@register.function
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
    base = context['request'].META['PATH_INFO']
    qs = cgi.parse_qs(context['request'].META['QUERY_STRING'])
    for key, value in kwargs.items():
        if value is None:
            # delete the parameter
            if key in qs:
                del qs[key]
        else:
            # change it
            qs[key] = value
    new_qs = urllib.urlencode(qs, True)
    if new_qs:
        return '%s?%s' % (base, new_qs)
    return base
