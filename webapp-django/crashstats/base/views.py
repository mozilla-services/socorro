from django import http
from django.conf import settings
from django.shortcuts import render


class CrashstatsHttpResponseBadRequest(http.HttpResponseBadRequest):
    """Override of the Django HttpResponseBadRequest that makes sure
    to set the content_type to "text/plain" if it hasn't already been
    set."""
    def __init__(self, *args, **kwargs):
        if 'content_type' not in kwargs:
            kwargs['content_type'] = 'text/plain; charset=UTF-8'
        super(CrashstatsHttpResponseBadRequest, self).__init__(*args, **kwargs)


def handler500(request):
    if getattr(request, '_json_view', False):
        # Every view with the `utils.json_view` decorator sets,
        # on the request object, that it wants to eventually return
        # a JSON output. Let's re-use that fact here.
        return http.JsonResponse({
            'error': 'Internal Server Error',
            'path': request.path,
            'query_string': request.META.get('QUERY_STRING'),
        }, status=500)
    context = {'product': settings.DEFAULT_PRODUCT}
    return render(request, '500.html', context, status=500)


def handler404(request):
    if getattr(request, '_json_view', False):
        # Every view with the `utils.json_view` decorator sets,
        # on the request object, that it wants to eventually return
        # a JSON output. Let's re-use that fact here.
        return http.JsonResponse({
            'error': 'Page not found',
            'path': request.path,
            'query_string': request.META.get('QUERY_STRING'),
        }, status=404)
    context = {'product': settings.DEFAULT_PRODUCT}
    return render(request, '404.html', context, status=404)
