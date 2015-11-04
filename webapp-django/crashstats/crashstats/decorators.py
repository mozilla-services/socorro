import functools

from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

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
        try:
            kwargs['default_context'] = utils.build_default_context(
                product,
                versions
            )
        except Http404 as e:
            # A 404 will be raised if the product doesn't exist, or if the
            # version does not exist for that product.
            # In the latter case, we want to redirect the user to that
            # product's home page. If the product is missing, superusers
            # should be sent to the admin panel to add that product, while
            # regular users will see a 404.
            if 'version' in str(e):
                return redirect(reverse('crashstats:home', args=(product,)))
            elif request.user.is_superuser:
                url = '%s?product=%s' % (reverse('manage:products'), product)
                return redirect(url)
            raise
        return view(request, *args, **kwargs)
    return inner
