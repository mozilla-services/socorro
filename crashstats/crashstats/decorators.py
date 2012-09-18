import functools
from django import http

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
                    request.days = int(request.REQUEST.get('days', default))
                except ValueError:
                    return http.HttpResponseBadRequest(
                        "'days' not a number"
                    )
                if request.days not in possible_days:
                    return http.HttpResponseBadRequest(
                        "'days' not a recognized number"
                    )
            else:
                if default is _marker:
                    return http.HttpResponseBadRequest(
                        "'days' missing from request"
                    )
                request.days = default
            request.possible_days = possible_days

            return view(request, *args, **kwargs)
        return inner
    return outer
