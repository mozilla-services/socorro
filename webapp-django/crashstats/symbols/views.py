import gzip
import os
import mimetypes
import fnmatch
from functools import wraps
from cStringIO import StringIO
from zipfile import BadZipfile

from django import http
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.models import Permission
from django.contrib.auth.decorators import permission_required
from django.contrib.sites.requests import RequestSite
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ImproperlyConfigured

import boto
import boto.s3.connection
import boto.exception

from crashstats.crashstats.decorators import login_required
from crashstats.tokens.models import Token
from . import models
from . import forms
from . import utils


def api_login_required(view_func):
    """similar to django.contrib.auth.decorators.login_required
    except instead of redirecting it returns a 403 message if not
    authenticated."""
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        if not request.user.is_active:
            return http.HttpResponseForbidden(
                "This requires an Auth-Token to authenticate the request"
            )
        return view_func(request, *args, **kwargs)

    return inner


def check_symbols_archive_content(content):
    """return an error if there was something wrong"""
    for i, line in enumerate(content.splitlines()):
        for snippet in settings.DISALLOWED_SYMBOLS_SNIPPETS:
            if snippet in line:
                return (
                    "Content of archive file contains the snippet "
                    "'%s' which is not allowed\n" % snippet
                )


def unpack_and_upload(iterator, symbols_upload, bucket_name, bucket_location):
    necessary_setting_keys = (
        'AWS_ACCESS_KEY',
        'AWS_SECRET_ACCESS_KEY',
        'SYMBOLS_BUCKET_DEFAULT_LOCATION',
        'SYMBOLS_BUCKET_DEFAULT_NAME',
        'SYMBOLS_FILE_PREFIX',
    )
    for key in necessary_setting_keys:
        if not getattr(settings, key):
            raise ImproperlyConfigured(
                "Setting %s must be set" % key
            )

    conn = boto.connect_s3(
        settings.AWS_ACCESS_KEY,
        settings.AWS_SECRET_ACCESS_KEY,
        # Deliberately commented out until we know a better way to do
        # this. When connecting to S3 on a Python 2.7 on OSX, you can't
        # get buckets that dots in the name. But applying this calling_format
        # thing breaks on our Python 2.7 on production.
        # So it's commented out, in a rush, until we discover a unified
        # way of dealing with this on local dev environments as well
        # as in production.
        # calling_format=boto.s3.connection.OrdinaryCallingFormat(),
    )
    assert bucket_name

    bucket = conn.lookup(bucket_name)
    if bucket is None:
        try:
            bucket = conn.create_bucket(bucket_name, location=bucket_location)
        except AttributeError as exception:
            # This extra exception trap is temporary until we can figure
            # out why sometimes we get AttributeErrors here.
            raise AttributeError(
                '%s (bucket_name=%r, bucket_location=%r)' % (
                    exception, bucket_name, bucket_location
                )
            )

    total_uploaded = 0
    for member in iterator:
        key_name = os.path.join(
            settings.SYMBOLS_FILE_PREFIX, member.name
        )
        key = bucket.get_key(key_name)

        # let's assume first that we need to add a new key
        prefix = '+'
        if key:
            # key already exists, but is it the same size?
            if key.size != member.size:
                # file size in S3 is different, upload the new one
                key = None
            else:
                prefix = '='

        if not key:
            key = bucket.new_key(key_name)

            file = StringIO()
            file.write(member.extractor().read())

            content_type = mimetypes.guess_type(key_name)[0]  # default guess
            for ext in settings.SYMBOLS_MIME_OVERRIDES:
                if key_name.lower().endswith('.{0}'.format(ext)):
                    content_type = settings.SYMBOLS_MIME_OVERRIDES[ext]
                    key.content_type = content_type
                    symbols_upload.content_type = key.content_type

            compress = False
            for ext in settings.SYMBOLS_COMPRESS_EXTENSIONS:
                if key_name.lower().endswith('.{0}'.format(ext)):
                    compress = True
                    break
            headers = {
                'Content-Type': content_type,
            }
            if compress:
                headers['Content-Encoding'] = 'gzip'
                out = StringIO()
                with gzip.GzipFile(fileobj=out, mode='w') as f:
                    f.write(file.getvalue())
                value = out.getvalue()
            else:
                value = file.getvalue()
            uploaded = key.set_contents_from_string(value, headers)
            total_uploaded += uploaded

        symbols_upload.content += '%s%s,%s\n' % (
            prefix,
            key.bucket.name,
            key.key
        )
        symbols_upload.save()

    return total_uploaded


def get_bucket_name_and_location(user):
    """return a tuple of (name, location) that might depend on the
    user."""
    name = settings.SYMBOLS_BUCKET_DEFAULT_NAME
    location = settings.SYMBOLS_BUCKET_DEFAULT_LOCATION
    exceptions = dict(
        (x.lower(), y) for x, y in settings.SYMBOLS_BUCKET_EXCEPTIONS.items()
    )
    if user.email.lower() in exceptions:
        # easy
        exception = exceptions[user.email.lower()]
    else:
        # match against every possible wildcard
        exception = None  # assume no match
        for email_or_wildcard in settings.SYMBOLS_BUCKET_EXCEPTIONS:
            if fnmatch.fnmatch(user.email.lower(), email_or_wildcard.lower()):
                # a match!
                exception = settings.SYMBOLS_BUCKET_EXCEPTIONS[
                    email_or_wildcard
                ]
                break

    if exception:
        if '|' in exception:
            name, location = exception.split('|')
        else:
            name = exception
    return name, location


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
@transaction.atomic
def web_upload(request):
    context = {}
    if request.method == 'POST':
        form = forms.UploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                content = utils.preview_archive_content(
                    form.cleaned_data['file'].file,
                    form.cleaned_data['file'].name
                )
            except BadZipfile as exception:
                return http.HttpResponseBadRequest(exception)

            error = check_symbols_archive_content(content)
            if error:
                return http.HttpResponseBadRequest(error)

            symbols_upload = models.SymbolsUpload.objects.create(
                user=request.user,
                content='',
                size=form.cleaned_data['file'].size,
                filename=os.path.basename(form.cleaned_data['file'].name),
            )
            form.cleaned_data['file'].file.seek(0)
            bucket_name, bucket_location = get_bucket_name_and_location(
                request.user
            )
            unpack_and_upload(
                utils.get_archive_members(
                    form.cleaned_data['file'].file,
                    form.cleaned_data['file'].name
                ),
                symbols_upload,
                bucket_name,
                bucket_location
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
    """The page about doing an upload via things like curl"""
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
@api_login_required
@permission_required('crashstats.upload_symbols')
@transaction.atomic
def upload(request):
    for name in request.FILES:
        upload = request.FILES[name]
        size = upload.size
        break
    else:
        return http.HttpResponseBadRequest(
            "Must be multipart form data with key 'file'"
        )

    if not size:
        return http.HttpResponseBadRequest('File size 0')

    content = utils.preview_archive_content(upload, name)
    error = check_symbols_archive_content(content)
    if error:
        return http.HttpResponseBadRequest(error)

    symbols_upload = models.SymbolsUpload.objects.create(
        user=request.user,
        size=size,
        content='',
        filename=name,
    )
    bucket_name, bucket_location = get_bucket_name_and_location(
        request.user
    )
    unpack_and_upload(
        utils.get_archive_members(upload, name),
        symbols_upload,
        bucket_name,
        bucket_location
    )

    return http.HttpResponse('OK', status=201)


@login_required
def content(request, pk):
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
