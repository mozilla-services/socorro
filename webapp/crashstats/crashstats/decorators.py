# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import functools
import time
from urllib.parse import urlsplit

from markus.utils import generate_tag

from django.contrib.auth.decorators import REDIRECT_FIELD_NAME, user_passes_test
from django.http import HttpResponseBadRequest, Http404
from django.shortcuts import redirect
from django.urls import reverse

from crashstats.crashstats import utils
from socorro.libmarkus import METRICS


def login_required(
    function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None
):
    """This is a re-implementation of the ever useful default decorator
    in django.contrib.auth.decorators which is exactly the same except
    that it also requires the user to be active.

    In other words, if you use this decorator you're saying that
    being logged in AND being active is required.

    The usefulness of this is that super users can revoke a user being
    active and halt the user's access even after the user has logged in.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_active,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
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
            request_data = request.method == "GET" and request.GET or request.POST
            if "days" in request_data:
                try:
                    days = int(request_data.get("days", default))
                except ValueError:
                    return HttpResponseBadRequest("'days' not a number")
                if days not in possible_days:
                    return HttpResponseBadRequest("'days' not a recognized " "number")
            else:
                if default is _marker:
                    return HttpResponseBadRequest("'days' missing from " "request")
                days = default
            kwargs.update({"days": days, "possible_days": possible_days})
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
        product_name = kwargs.get("product", request.GET.get("product", None))
        versions = kwargs.get("versions", request.GET.get("versions", None))
        try:
            kwargs["default_context"] = utils.build_default_context(
                product_name, versions
            )
        except Http404 as e:
            # A 404 will be raised if the product doesn't exist, or if the version does
            # not exist for that product.
            #
            # In the latter case, we want to redirect the user to that product's home
            # page. If the product is missing, superusers should be sent to the admin
            # panel to add that product, while regular users will see a 404.
            if "version" in str(e):
                return redirect(
                    reverse("crashstats:product_home", args=(product_name,))
                )
            raise
        return view(request, *args, **kwargs)

    return inner


# List of url pattern names (see urls.py files) to use the url path
# instead of the resolver route
USE_PATH_VIEWS = [
    # The url arg is the API endpoint
    "model_wrapper",
    # The url arg is the product name
    "product_home",
]


@functools.cache
def cached_generate_tag(key, value):
    """Generates a tag set item

    This caches values so it works a little faster. This also strips out some
    additional characters from the tag value that we're having problems with.

    :param tag: the tag name as a string
    :param value: the tag value as a string

    :returns: tag set item

    """
    value = value or "novalue"
    return generate_tag(key, value=value)


def track_view(view):
    """Tracks timings, status codes, and AJAX for views.

    This takes into account paths that include arguments (e.g. report view which has
    crash ids) that we don't want to track individually as well as paths that include
    arguments (e.g. api model wrapper that has model name) that we do want to track
    individually.

    It does this by hard-coding the url names where we want to use request.path instead
    of request.resolver_match.route.

    """

    @functools.wraps(view)
    def inner(request, *args, **kwargs):
        start_time = time.time()
        response = view(request, *args, **kwargs)

        is_ajax = False
        referer = request.headers.get("Referer")
        if referer:
            # If the referer host is the same as the request host that implies that the
            # API was used as an AJAX request in our main webapp itself.
            referer_host = urlsplit(referer).netloc
            if referer_host == request.headers.get("Host"):
                is_ajax = True

        # Flag indicating whether this was an api so we can differentiate between API
        # and non-API things
        is_api = request.path.startswith("/api/")

        # We track page views by the resolver route. That way the page doesn't include
        # things like crash ids. However, with the model wrapper API views, we want to
        # include the model name argument.
        if (
            request.resolver_match
            and request.resolver_match.url_name not in USE_PATH_VIEWS
        ):
            path = "/" + request.resolver_match.route
        else:
            path = request.path

        delta = (time.time() - start_time) * 1000
        METRICS.timing(
            "webapp.view.pageview",
            value=delta,
            tags=[
                cached_generate_tag("ajax", value=str(is_ajax).lower()),
                cached_generate_tag("api", value=str(is_api).lower()),
                cached_generate_tag("path", value=path),
                cached_generate_tag("status", value=str(response.status_code)),
            ],
        )

        return response

    return inner
