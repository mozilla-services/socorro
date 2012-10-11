from django.conf import settings
from django.shortcuts import render


def handler500(request):
    data = {'product': settings.DEFAULT_PRODUCT}
    return render(request, '500.html', data, status=500)
