from django import http
from django.shortcuts import render


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
    context = {}
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
    context = {}
    return render(request, '404.html', context, status=404)
