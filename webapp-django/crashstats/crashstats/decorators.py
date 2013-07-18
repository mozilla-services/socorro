import functools

from django.http import HttpResponseBadRequest

from . import utils

_marker = object()


# XXX: we could break out 'days' here as a configurable parameter instead
def check_days_parameter(possible_days, default=_marker):
    """Return a decorator that checks the `days` parameter from the request
    and barfs if it's not valid or otherwise makes sure it's an integer.
    """
    def outer(view):
        @functools.wraps(view)
        def inner(request, *args, **kwargs):
            if 'days' in request.REQUEST:
                try:
                    days = int(request.REQUEST.get('days', default))
                except ValueError:
                    return HttpResponseBadRequest("'days' not a number")
                if days not in possible_days:
                    return HttpResponseBadRequest("'days' not a recognized "
                                                  "number")
            else:
                if default is _marker:
                    return HttpResponseBadRequest("'days' missing from "
                                                  "request")
                days = default
            kwargs.update({'days': days, 'possible_days': possible_days})
            return view(request, *args, **kwargs)
        return inner
    return outer


def pass_default_context(view):
    """
    A decorator that prefills the default template context depending on
    the views product and versions parameters.
    """
    @functools.wraps(view)
    def inner(request, *args, **kwargs):
        product = kwargs.get('product', None)
        versions = kwargs.get('versions', None)
        kwargs['default_context'] = utils.build_default_context(product,
                                                                versions)
        return view(request, *args, **kwargs)
    return inner
