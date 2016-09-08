import functools
import urlparse

from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import (
    REDIRECT_FIELD_NAME,
    user_passes_test,
)

from . import utils
from crashstats.base import ga


def login_required(
    function=None,
    redirect_field_name=REDIRECT_FIELD_NAME,
    login_url=None
):
    """This is a re-implementation of the ever useful default decorator
    in django.contrib.auth.decorators which is exactly the same except
    that it also requires the user to be active.

    In other words, if you use this decorator you're saying that
    being logged in AND being active is required.

    The usefulness of this is that super users can revoke a user being
    active and halt the user's access even after the user has signed in.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_active,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


_marker = object()


# XXX: we could break out 'days' here as a configurable parameter instead
def check_days_parameter(possible_days, default=_marker):
    """Return a decorator that checks the `days` parameter from the request
    and barfs if it's not valid or otherwise makes sure it's an integer.
    """
    def outer(view):
        @functools.wraps(view)
        def inner(request, *args, **kwargs):
            request_data = (
                request.method == 'GET' and request.GET or request.POST
            )
            if 'days' in request_data:
                try:
                    days = int(request_data.get('days', default))
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
                return redirect(reverse('home:home', args=(product,)))
            elif request.user.is_superuser:
                url = '%s?product=%s' % (reverse('manage:products'), product)
                return redirect(url)
            raise
        return view(request, *args, **kwargs)
    return inner


def track_api_pageview(view):
    @functools.wraps(view)
    def inner(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        if response.status_code < 500:
            referer = request.META.get('HTTP_REFERER')
            if referer:
                # If the referer host is the same as the request host
                # that implies that the API was used as an AJAX request
                # in our main webapp itself. If so, don't track.
                referer_host = urlparse.urlparse(referer).netloc
                if referer_host == request.META.get('HTTP_HOST'):
                    return response
            ga.track_api_pageview(request)
        return response
    return inner
