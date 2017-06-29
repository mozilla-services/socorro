import collections
import copy
import hashlib
import math
import urllib

from django import http
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.core.cache import cache
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone

from eventlog.models import log, Log

from crashstats.crashstats.models import (
    ProductVersions,
    Releases,
    GraphicsDevices,
    Platforms,
    Reprocessing,
)
from crashstats.supersearch.models import (
    SuperSearch,
    SuperSearchField,
    SuperSearchFields,
    SuperSearchMissingFields,
)
from crashstats.tokens.models import Token
from crashstats.status.models import StatusMessage
from crashstats.symbols.models import SymbolsUpload
from crashstats.crashstats.utils import json_view
from crashstats.manage.decorators import superuser_required

from . import forms
from . import utils


def notice_change(before, after):
    assert before.__class__ == after.__class__
    changes = {}
    if isinstance(before, User) or isinstance(before, Group):
        for fieldname in before._meta.get_all_field_names():

            v1 = getattr(before, fieldname, None)
            v2 = getattr(after, fieldname, None)
            if hasattr(v1, 'all'):
                # many-to-many field!
                # To be able to compare, the many-to-many field needs to
                # have been converted to a list and attached to the object.
                # If we don't do this, we won't notice the difference.
                # Remember that many-to-many fields are stored in a different
                # table. E.g. for a User:
                #
                #  user_id | group_id
                #  --------|---------
                #  3       | 45
                #  3       | 89
                #
                # And all you have is a User instance with the ID 3,
                # you can't find out what was in that many-to-many mapping
                # table before because now it's 45 and 89.
                # So it must have been expanded into a Python list and
                # attached to the object itself.
                if not hasattr(before, '__%s' % fieldname):
                    continue
                # these have to have been expanded before!
                v1 = getattr(before, '__%s' % fieldname)

                v2 = getattr(
                    after,
                    '__%s' % fieldname,
                    [unicode(x) for x in v2.all()]
                )

            if v1 != v2:
                changes[fieldname] = [v1, v2]
        return changes
    raise NotImplementedError(before.__class__.__name__)


@superuser_required
def home(request, default_context=None):
    context = default_context or {}
    return render(request, 'manage/home.html', context)


@superuser_required
def users(request):
    context = {}
    context['all_groups'] = Group.objects.all().order_by('name')
    return render(request, 'manage/users.html', context)


@json_view
@superuser_required
def users_data(request):
    order_by = request.GET.get('order_by', 'last_login')
    assert order_by in ('last_login', 'email')
    if order_by == 'last_login':
        order_by = '-last_login'
    form = forms.FilterUsersForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))
    users_ = User.objects.all().order_by(order_by)
    if form.cleaned_data['email']:
        users_ = users_.filter(email__icontains=form.cleaned_data['email'])
    if form.cleaned_data['superuser'] is not None:
        users_ = users_.filter(is_superuser=form.cleaned_data['superuser'])
    if form.cleaned_data['active'] is not None:
        users_ = users_.filter(is_active=form.cleaned_data['active'])
    if form.cleaned_data['group']:
        users_ = users_.filter(groups=form.cleaned_data['group'])

    try:
        page = int(request.GET.get('page', 1))
        assert page >= 1
    except (ValueError, AssertionError):
        return http.HttpResponseBadRequest('invalid page')

    count = users_.count()
    user_items = []
    batch_size = settings.USERS_ADMIN_BATCH_SIZE
    m = (page - 1) * batch_size
    n = page * batch_size
    for user in users_[m:n]:
        user_items.append({
            'id': user.pk,
            'email': user.email,
            'is_superuser': user.is_superuser,
            'is_active': user.is_active,
            'last_login': user.last_login,
            'groups': [
                {'id': x.id, 'name': x.name}
                for x in user.groups.all()
            ]
        })
    return {
        'users': user_items,
        'count': count,
        'batch_size': batch_size,
        'page': page,
    }


@json_view
@superuser_required
@transaction.atomic
def user(request, id):
    context = {}
    user_ = get_object_or_404(User, id=id)
    if request.method == 'POST':
        # make a copy because it's mutable in the form
        before = copy.copy(user_)
        # expand the many-to-many field before changing it in the form
        before.__groups = [unicode(x) for x in before.groups.all()]

        form = forms.EditUserForm(request.POST, instance=user_)
        if form.is_valid():
            form.save()
            log(request.user, 'user.edit', {
                'change': notice_change(before, user_),
                'id': user_.id,
            })
            messages.success(
                request,
                'User %s update saved.' % user_.email
            )
            return redirect('manage:users')
    else:
        form = forms.EditUserForm(instance=user_)
    context['form'] = form
    context['edit_user'] = user_
    return render(request, 'manage/user.html', context)


@transaction.atomic
@superuser_required
def groups(request):
    context = {}
    if request.method == 'POST':
        if request.POST.get('delete'):
            group = get_object_or_404(Group, pk=request.POST['delete'])
            group.delete()
            log(request.user, 'group.delete', {'name': group.name})
            messages.success(
                request,
                'Group deleted.'
            )
            return redirect('manage:groups')
        form = forms.GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            log(request.user, 'group.add', {
                'id': group.id,
                'name': group.name,
                'permissions': [x.name for x in group.permissions.all()]
            })
            messages.success(
                request,
                'Group created.'
            )
            return redirect('manage:groups')
    else:
        form = forms.GroupForm()
    context['form'] = form
    context['groups'] = Group.objects.all().order_by('name')
    context['permissions'] = Permission.objects.all().order_by('name')
    return render(request, 'manage/groups.html', context)


@superuser_required
def group(request, id):
    context = {}
    group_ = get_object_or_404(Group, id=id)
    if request.method == 'POST':
        before = copy.copy(group_)
        before.__permissions = [x.name for x in before.permissions.all()]
        # print "permissions before", before.permissions.all()
        form = forms.GroupForm(request.POST, instance=group_)
        if form.is_valid():
            form.save()
            # print "permissions after", group_.permissions.all()
            group_.__permissions = [x.name for x in group_.permissions.all()]
            log(request.user, 'group.edit', {
                'id': group_.id,
                'change': notice_change(before, group_),
            })
            messages.success(
                request,
                'Group saved.'
            )
            return redirect('manage:groups')
    else:
        form = forms.GroupForm(instance=group_)
    context['form'] = form
    context['group'] = group_
    return render(request, 'manage/group.html', context)


@superuser_required
def analyze_model_fetches(request):
    context = {}
    all_ = cache.get('all_classes') or []
    records = []
    for item in all_:
        itemkey = hashlib.md5(item.encode('utf-8')).hexdigest()

        data = {}
        data['times'] = {}
        data['times']['hits'] = cache.get('times_HIT_%s' % itemkey, 0)
        data['times']['misses'] = cache.get('times_MISS_%s' % itemkey, 0)
        data['times']['both'] = (
            data['times']['hits'] + data['times']['misses']
        )
        data['uses'] = {}
        data['uses']['hits'] = cache.get('uses_HIT_%s' % itemkey, 0)
        data['uses']['misses'] = cache.get('uses_MISS_%s' % itemkey, 0)
        data['uses']['both'] = (
            data['uses']['hits'] + data['uses']['misses']
        )
        data['uses']['hits_percentage'] = (
            data['uses']['both'] and
            round(
                100.0 * data['uses']['hits'] / data['uses']['both'],
                1
            ) or
            'n/a'
        )
        records.append((item, data))
    context['records'] = records
    return render(request, 'manage/analyze-model-fetches.html', context)


@superuser_required
def graphics_devices(request):
    context = {}
    form = forms.GraphicsDeviceForm()
    upload_form = forms.GraphicsDeviceUploadForm()

    if request.method == 'POST' and 'file' in request.FILES:
        upload_form = forms.GraphicsDeviceUploadForm(
            request.POST,
            request.FILES
        )
        if upload_form.is_valid():
            if upload_form.cleaned_data['database'] == 'pcidatabase.com':
                function = utils.pcidatabase__parse_graphics_devices_iterable
            else:
                function = utils.pci_ids__parse_graphics_devices_iterable

            payload = list(function(upload_form.cleaned_data['file']))
            api = GraphicsDevices()
            result = api.post(data=payload)
            log(request.user, 'graphicsdevices.post', {
                'success': result,
                'database': upload_form.cleaned_data['database'],
                'no_lines': len(payload),
            })
            messages.success(
                request,
                'Graphics device CSV upload successfully saved.'
            )
            return redirect('manage:graphics_devices')

    elif request.method == 'POST':
        form = forms.GraphicsDeviceForm(request.POST)
        if form.is_valid():
            payload = [{
                'vendor_hex': form.cleaned_data['vendor_hex'],
                'adapter_hex': form.cleaned_data['adapter_hex'],
                'vendor_name': form.cleaned_data['vendor_name'],
                'adapter_name': form.cleaned_data['adapter_name'],
            }]
            api = GraphicsDevices()
            result = api.post(data=payload)
            log(request.user, 'graphicsdevices.add', {
                'payload': payload,
                'success': result
            })
            if result:
                messages.success(
                    request,
                    'Graphics device saved.'
                )
            return redirect('manage:graphics_devices')

    context['page_title'] = "Graphics Devices"
    context['form'] = form
    context['upload_form'] = upload_form
    return render(request, 'manage/graphics_devices.html', context)


@json_view
@superuser_required
def graphics_devices_lookup(request):
    form = forms.GraphicsDeviceLookupForm(request.GET)
    if form.is_valid():
        vendor_hex = form.cleaned_data['vendor_hex']
        adapter_hex = form.cleaned_data['adapter_hex']
        api = GraphicsDevices()
        result = api.get(vendor_hex=vendor_hex, adapter_hex=adapter_hex)
        return result
    else:
        return http.HttpResponseBadRequest(str(form.errors))


@superuser_required
def symbols_uploads(request):
    context = {}
    context['page_title'] = "Symbols Uploads"
    return render(request, 'manage/symbols_uploads.html', context)


@superuser_required
@json_view
def symbols_uploads_data(request):
    try:
        page = int(request.GET.get('page', 1))
        assert page >= 1
    except (ValueError, AssertionError):
        return http.HttpResponseBadRequest('invalid page')

    form = forms.FilterSymbolsUploadsForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    uploads = (
        SymbolsUpload.objects.all()
        .select_related('user')
        .order_by('-created')
    )
    if form.cleaned_data['email']:
        uploads = uploads.filter(
            user__email__icontains=form.cleaned_data['email']
        )
    if form.cleaned_data['filename']:
        uploads = uploads.filter(
            filename__icontains=form.cleaned_data['filename']
        )
    if form.cleaned_data['content']:
        uploads = uploads.filter(
            content__contains=form.cleaned_data['content']
        )

    count = uploads.count()
    items = []
    batch_size = settings.SYMBOLS_UPLOADS_ADMIN_BATCH_SIZE
    m = (page - 1) * batch_size
    n = page * batch_size
    for upload in uploads[m:n]:
        items.append({
            'user': {
                'email': upload.user.email,
                'id': upload.user.pk,
                'url': reverse('manage:user', args=(upload.user.pk,)),
            },
            'id': upload.pk,
            'filename': upload.filename,
            'size': upload.size,
            'created': upload.created,
            'url': reverse('symbols:content', args=(upload.id,)),
        })
    return {
        'items': items,
        'count': count,
        'batch_size': batch_size,
        'page': page,
    }


@superuser_required
def supersearch_fields(request):
    context = {}
    sorted_fields = sorted(
        SuperSearchFields().get().values(),
        key=lambda x: x['name'].lower()
    )
    context['fields'] = sorted_fields
    return render(request, 'manage/supersearch_fields.html', context)


def _get_supersearch_field_data(source):
    form = forms.SuperSearchFieldForm(source)

    if not form.is_valid():
        return str(form.errors)

    return form.cleaned_data


def _delete_supersearch_fields_api_cache(namespace=None):
    # The API is using cache to get all fields by a specific namespace
    # for the whitelist lookup, clear that cache too.
    if namespace:
        cache.delete('api_supersearch_fields_{}'.format(namespace))
    cache.delete('api_supersearch_fields')


@superuser_required
def supersearch_fields_missing(request):
    context = {}
    missing_fields = SuperSearchMissingFields().get()

    context['missing_fields'] = missing_fields['hits']
    context['missing_fields_count'] = missing_fields['total']

    return render(request, 'manage/supersearch_fields_missing.html', context)


@superuser_required
def products(request):
    context = {}
    api = ProductVersions()
    if request.method == 'POST':
        existing_products = set(
            x['product'] for x in api.get()['hits']
        )
        form = forms.ProductForm(
            request.POST,
            existing_products=existing_products
        )
        if form.is_valid():
            api.post(
                product=form.cleaned_data['product'],
                version=form.cleaned_data['initial_version']
            )
            log(request.user, 'product.add', form.cleaned_data)
            messages.success(
                request,
                'Product %s (%s) added.' % (
                    form.cleaned_data['product'],
                    form.cleaned_data['initial_version']
                )
            )
            return redirect('manage:products')
    else:
        product = request.GET.get('product')
        if product is not None:
            messages.error(
                request,
                'Product %s not found. Submit the form below to add it.' % (
                    product
                )
            )
        form = forms.ProductForm(initial={
            'product': product,
            'initial_version': '1.0'
        })
    context['form'] = form
    context['page_title'] = "Products"
    return render(request, 'manage/products.html', context)


@superuser_required
def releases(request):
    context = {}
    platforms_api = Platforms()
    platform_names = [x['name'] for x in platforms_api.get()]

    if request.method == 'POST':
        form = forms.ReleaseForm(
            request.POST,
            platforms=platform_names
        )
        if form.is_valid():
            api = Releases()
            api.post(
                product=form.cleaned_data['product'],
                version=form.cleaned_data['version'],
                update_channel=form.cleaned_data['update_channel'],
                build_id=form.cleaned_data['build_id'],
                platform=form.cleaned_data['platform'],
                beta_number=form.cleaned_data['beta_number'],
                release_channel=form.cleaned_data['release_channel'],
                throttle=form.cleaned_data['throttle'],
            )
            log(request.user, 'release.add', form.cleaned_data)
            messages.success(
                request,
                'New release for %s:%s added.' % (
                    form.cleaned_data['product'],
                    form.cleaned_data['version']
                )
            )
            return redirect('manage:releases')
    else:
        form = forms.ReleaseForm(
            platforms=platform_names,
            initial={
                'throttle': 1,
                'update_channel': 'Release',
                'release_channel': 'release',
            }
        )

    context['form'] = form
    context['page_title'] = "Releases"
    return render(request, 'manage/releases.html', context)


@superuser_required
def events(request):
    context = {}

    # The reason we can't use `.distinct('action')` is because
    # many developers use sqlite for local development and
    # that's not supported.
    # If you use postgres, `Log.objects.all().values('action').distinct()`
    # will actually return a unique list of dicts.
    # Either way it's no inefficient convert it to a set and back to a list
    # because there are so few in local dev and moot in prod.
    context['all_actions'] = list(set([
        x['action'] for x in
        Log.objects.all().values('action').distinct()
    ]))
    return render(request, 'manage/events.html', context)


@json_view
@superuser_required
def events_data(request):
    form = forms.FilterEventsForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))
    events_ = Log.objects.all()
    if form.cleaned_data['user']:
        events_ = events_.filter(
            user__email__icontains=form.cleaned_data['user']
        )
    if form.cleaned_data['action']:
        events_ = events_.filter(
            action=form.cleaned_data['action']
        )
    count = events_.count()
    try:
        page = int(request.GET.get('page', 1))
        assert page >= 1
    except (ValueError, AssertionError):
        return http.HttpResponseBadRequest('invalid page')
    items = []
    batch_size = settings.EVENTS_ADMIN_BATCH_SIZE
    batch = Paginator(events_.select_related('user'), batch_size)
    batch_page = batch.page(page)

    def _get_edit_url(action, extra):
        if action == 'user.edit' and extra.get('id'):
            return reverse('manage:user', args=(extra.get('id'),))
        if action in ('group.edit', 'group.add') and extra.get('id'):
            return reverse('manage:group', args=(extra.get('id'),))
        if (
            action in ('supersearch_field.post', 'supersearch_field.put') and
            extra.get('name')
        ):
            return (
                reverse('manage:supersearch_field') + '?' +
                urllib.urlencode({'name': extra.get('name')})
            )

    for event in batch_page.object_list:
        items.append({
            'user': event.user.email,
            'timestamp': event.timestamp.isoformat(),
            'action': event.action,
            'extra': event.extra,
            'url': _get_edit_url(event.action, event.extra)
        })

    return {
        'events': items,
        'count': count,
        'batch_size': batch_size,
        'page': page,
    }


@superuser_required
@transaction.atomic
def api_tokens(request):
    all_possible_permissions = (
        Permission.objects.filter(content_type__model='')
        .order_by('name')
    )
    possible_permissions = []
    for permission in all_possible_permissions:
        possible_permissions.append(permission)

    expires_choices = (
        (1, '1 day'),
        (7, '1 week'),
        (30, '1 month'),
        (30 * 3, '3 months'),
        (365, '1 year'),
        (365 * 10, '10 years'),
    )

    if request.method == 'POST':
        form = forms.APITokenForm(
            request.POST,
            possible_permissions=possible_permissions,
            expires_choices=expires_choices,
        )
        if form.is_valid():
            data = form.cleaned_data
            token = Token.objects.create(
                user=data['user'],
                notes=data['notes'],
                expires=data['expires'],
            )
            for permission in data['permissions']:
                token.permissions.add(permission)

            log(request.user, 'api_token.create', {
                'user': token.user.email,
                'expires': token.expires,
                # Do this reverse trick to avoid microseconds rounding it
                # down to 6 days.
                'expires_days': (timezone.now() - token.expires).days * -1,
                'notes': token.notes,
                'permissions': ', '.join(
                    x.name for x in token.permissions.all()
                ),
            })

            messages.success(
                request,
                'API Token for %s created. ' % token.user.email
            )
            return redirect('manage:api_tokens')
    else:
        form = forms.APITokenForm(
            possible_permissions=possible_permissions,
            expires_choices=expires_choices,
            initial={
                'expires': settings.TOKENS_DEFAULT_EXPIRATION_DAYS,
            }
        )
    context = {
        'form': form,
        'filter_form': forms.FilterAPITokensForm(request.GET),
    }
    return render(request, 'manage/api_tokens.html', context)


@require_POST
@json_view
@superuser_required
def api_tokens_delete(request):
    if not request.POST.get('id'):
        return http.HttpResponseBadRequest('No id')
    token = get_object_or_404(Token, id=request.POST['id'])

    log(request.user, 'api_token.delete', {
        'user': token.user.email,
        'permissions': ', '.join(
            x.name for x in token.permissions.all()
        ),
        'notes': token.notes,
    })

    token.delete()
    return True


@json_view
@superuser_required
def api_tokens_data(request):
    form = forms.FilterAPITokensForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    tokens = Token.objects.all().order_by('-created')
    if form.cleaned_data['user']:
        tokens = tokens.filter(
            user__email__icontains=form.cleaned_data['user']
        )
    if form.cleaned_data['key']:
        tokens = tokens.filter(
            key__startswith=form.cleaned_data['key']
        )
    if form.cleaned_data['expired'] == 'yes':
        tokens = tokens.filter(
            expires__lt=timezone.now()
        )
    elif form.cleaned_data['expired'] == 'no':
        tokens = tokens.filter(
            expires__gte=timezone.now()
        )
    count = tokens.count()
    try:
        page = int(request.GET.get('page', 1))
        assert page >= 1
    except (ValueError, AssertionError):
        return http.HttpResponseBadRequest('invalid page')

    items = []
    batch_size = settings.API_TOKENS_ADMIN_BATCH_SIZE
    batch = Paginator(tokens.select_related('user'), batch_size)
    batch_page = batch.page(page)

    # build up a dict of permission id -> permission name
    _permissions_names = {}
    for permission in Permission.objects.filter(content_type__model=''):
        _permissions_names[permission.id] = permission.name

    # build up a dict of token id -> permission names
    _permissions_map = collections.defaultdict(list)
    # ...but only do it for the subset of tokens we'll look at
    token_permissions = (
        Token.permissions.through.objects.filter(token__in=tokens)
    )
    for x in token_permissions:
        _permissions_map[x.token_id].append(
            _permissions_names[x.permission_id]
        )

    for token in batch_page.object_list:
        items.append({
            'id': token.id,
            'user': token.user.email,
            'key': token.key,
            'expires': token.expires,
            'expired': token.is_expired,
            'permissions': sorted(_permissions_map.get(token.id, [])),
            'notes': token.notes,
            'created': token.created,
        })

    return {
        'tokens': items,
        'count': count,
        'batch_size': batch_size,
        'page': page,
    }


@superuser_required
def crash_me_now(request):
    if request.method == 'POST':
        form = forms.CrashMeNowForm(request.POST)
        if form.is_valid():
            klass = {
                'NameError': NameError,
                'ValueError': ValueError,
                'AttributeError': AttributeError
            }.get(form.cleaned_data['exception_type'])
            # crash now!
            raise klass(form.cleaned_data['exception_value'])
    else:
        initial = {
            'exception_type': 'NameError',
            'exception_value': 'Webapp Crash Me Now test error',
        }
        form = forms.CrashMeNowForm(initial=initial)
    context = {'form': form}
    return render(request, 'manage/crash_me_now.html', context)


@superuser_required
def reprocessing(request):
    if request.method == 'POST':
        form = forms.ReprocessingForm(request.POST)
        if form.is_valid():
            crash_id = form.cleaned_data['crash_id']
            url = reverse('manage:reprocessing')
            worked = Reprocessing().post(crash_ids=[crash_id])
            if worked:
                url += '?crash_id={}'.format(crash_id)
                messages.success(
                    request,
                    '{} sent in for reprocessing.'.format(crash_id)
                )
            else:
                messages.error(
                    request,
                    'Currently unable to send in the crash ID '
                    'for reprocessing.'
                )
            log(request.user, 'reprocessing', {
                'crash_id': crash_id,
                'worked': worked,
            })

            return redirect(url)
    else:
        form = forms.ReprocessingForm()
    context = {
        'form': form,
        'crash_id': request.GET.get('crash_id'),
    }
    return render(request, 'manage/reprocessing.html', context)


@superuser_required
@transaction.atomic
def status_message(request):
    if request.method == 'POST':
        form = forms.StatusMessageForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            status = StatusMessage.objects.create(
                message=data['message'],
                severity=data['severity'],
            )

            log(request.user, 'status_message.create', {
                'user': request.user.email,
                'severity': status.severity,
            })

            messages.success(
                request,
                'Status Message created. '
            )
            return redirect('manage:status_message')
    else:
        form = forms.StatusMessageForm()

    try:
        page = int(request.GET.get('page', 1))
        assert page >= 1
    except (ValueError, AssertionError):
        return http.HttpResponseBadRequest('invalid page')

    statuses = (
        StatusMessage.objects.all().order_by('-created_at')
    )

    count = statuses.count()
    batch_size = settings.STATUS_MESSAGE_ADMIN_BATCH_SIZE
    m = (page - 1) * batch_size
    n = page * batch_size

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']
    current_url = '{}?{}'.format(
        reverse('manage:status_message'),
        current_query.urlencode()
    )

    context = {
        'form': form,
        'statuses': statuses[m:n],
        'pagination_data': {
            'page': page,
            'current_url': current_url,
            'total_pages': int(math.ceil(float(count) / batch_size)),
            'total_count': count,
        }
    }
    return render(request, 'manage/status_message.html', context)


@superuser_required
@require_POST
@transaction.atomic
def status_message_disable(request, id):
    status = get_object_or_404(StatusMessage, id=id)

    log(request.user, 'status_message.disable', {
        'user': request.user.email,
        'id': status.id,
    })

    status.enabled = False
    status.save()

    messages.success(
        request,
        'Status message successfully disabled.'
    )

    return redirect(reverse('manage:status_message'))
