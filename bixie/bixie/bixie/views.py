from django.shortcuts import render

import commonware


log = commonware.log.getLogger('playdoh')


def home(request):
    """Main view."""
    data = {}
    return render(request, 'bixie/home.html', data)


def list(request):
    """List view"""
    data = {}
    return render(request, 'bixie/report_list.html', data)
