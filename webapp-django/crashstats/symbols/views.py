import os
from cStringIO import StringIO

from django import http
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.models import Permission
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.sites.models import RequestSite
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db import transaction

from crashstats.tokens.models import Token
from . import models
from . import forms
from . import utils


@login_required
def home(request):
    context = {}

    context['your_uploads'] = (
        models.SymbolsUpload.objects
        .filter(user=request.user)
        .order_by('-created')
    )
    context['permission'] = Permission.objects.get(codename='upload_symbols')
    context['symbols_request_link'] = getattr(
        settings,
        'SYMBOLS_PERMISSION_HINT_LINK',
        None
    )

    return render(request, 'symbols/home.html', context)


@login_required
@permission_required('crashstats.upload_symbols')
@transaction.commit_on_success
def web_upload(request):
    context = {}
    if request.method == 'POST':
        form = forms.UploadForm(request.POST, request.FILES)
        if form.is_valid():
            symbols_upload = models.SymbolsUpload.objects.create(
                user=request.user,
                content=utils.preview_archive_content(
                    form.cleaned_data['file'].file,
                    form.cleaned_data['file'].content_type
                ),
                size=form.cleaned_data['file'].size,
                filename=os.path.basename(form.cleaned_data['file'].name),
                file=form.cleaned_data['file'],
            )
            messages.success(
                request,
                '%s bytes of %s uploaded.' % (
                    symbols_upload.size,
                    symbols_upload.filename
                )
            )
            return redirect('symbols:home')
    else:
        form = forms.UploadForm()

    context['form'] = form

    return render(request, 'symbols/web_upload.html', context)


@login_required
@permission_required('crashstats.upload_symbols')
def api_upload(request):
    context = {}
    has_possible_token = False
    required_permission = Permission.objects.get(codename='upload_symbols')
    for token in Token.objects.active().filter(user=request.user):
        if token.permissions.filter(codename='upload_symbols'):
            has_possible_token = True
    context['has_possible_token'] = has_possible_token
    context['required_permission'] = required_permission
    context['absolute_base_url'] = (
        '%s://%s' % (
            request.is_secure() and 'https' or 'http',
            RequestSite(request).domain
        )
    )
    return render(request, 'symbols/api_upload.html', context)


@require_POST
@csrf_exempt
@permission_required('crashstats.upload_symbols')
@transaction.commit_on_success
def upload(request):
    for name in request.FILES:
        upload = request.FILES[name]
        size = upload.size
        break
    else:
        name = 'temp.zip'
        body = request.body
        size = len(body)
        upload = StringIO(body)

    if not size:
        return http.HttpResponseBadRequest('File size 0')

    content = utils.preview_archive_content(
        upload,
        utils.filename_to_mimetype(name)
    )

    models.SymbolsUpload.objects.create(
        user=request.user,
        size=size,
        content=content,
        filename=name,
        file=upload,
    )

    return http.HttpResponse('OK', status=201)


@login_required
def download(request, pk):
    symbols_upload = get_object_or_404(
        models.SymbolsUpload,
        pk=pk
    )
    if not request.user.is_superuser:
        if symbols_upload.user != request.user:
            return http.HttpResponseForbidden('Not yours')
    response = http.HttpResponse(
        symbols_upload.file.read(),
        content_type=utils.filename_to_mimetype(symbols_upload.filename)
    )
    response['Content-Disposition'] = (
        'attachment; filename="%s"' % (symbols_upload.filename,)
    )
    return response


@login_required
def preview(request, pk):
    symbols_upload = get_object_or_404(
        models.SymbolsUpload,
        pk=pk
    )
    if not request.user.is_superuser:
        if symbols_upload.user != request.user:
            return http.HttpResponseForbidden('Not yours')
    return http.HttpResponse(
        symbols_upload.content,
        content_type='text/plain'
    )
