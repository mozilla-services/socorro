from django.shortcuts import render

from crashstats.manage.decorators import superuser_required


@superuser_required
def home(request, default_context=None):
    context = default_context or {}
    return render(request, 'manage/home.html', context)
