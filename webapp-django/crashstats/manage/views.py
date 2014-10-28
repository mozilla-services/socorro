import json
import datetime
import functools
import copy
import urllib

from django import http
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User, Group, Permission
from django.core.cache import cache
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.core.paginator import Paginator

from eventlog.models import log, Log

from crashstats.crashstats.models import (
    CurrentProducts,
    Releases,
    ReleasesFeatured,
    Field,
    SkipList,
    GraphicsDevices,
    Platforms
)
from crashstats.supersearch.models import (
    SuperSearchField,
    SuperSearchFields,
    SuperSearchMissingFields,
)
from crashstats.symbols.models import SymbolsUpload
from crashstats.crashstats.utils import json_view
from . import forms
from .utils import parse_graphics_devices_iterable


def notice_change(before, after):
    assert before.__class__ == after.__class__
    changes = {}
    if isinstance(before, User) or isinstance(before, Group):
        # print dir(before)
        # print repr(before._meta)
        # print dir(before._meta)
        # print before._meta.get_all_field_names()
        for fieldname in before._meta.get_all_field_names():

            v1 = getattr(before, fieldname, None)
            v2 = getattr(after, fieldname, None)
            if hasattr(v1, 'all'):
                # many-to-many field!
                # To be able to compare the list must have been
                # field must have been expanded beforehand.
                # If it hasn't we can't compare.
                if not hasattr(before, '__%s' % fieldname):
                    continue
                # these have to have been expanded before!
                v1 = getattr(before, '__%s' % fieldname)

                v2 = getattr(
                    after,
                    '__%s' % fieldname,
                    [unicode(x) for x in v2.all()]
                )
                # v2 = [x.id for x in v2.all()]

            # print "\t%s:"%fieldname, (v1, v2),
            # print v1 == v2
            if v1 != v2:
                changes[fieldname] = [v1, v2]
        # print before._meta.get_all_related_objects_with_model()
        # print before._meta.get_all_related_objects()
        # print before._meta.get_all_related_many_to_many_objects()
        return changes
    raise NotImplementedError(before.__class__.__name__)


def superuser_required(view_func):
    @functools.wraps(view_func)
    def inner(request, *args, **kwargs):
        if not request.user.is_authenticated():
            return redirect(settings.LOGIN_URL)
        elif not request.user.is_superuser:
            messages.error(
                request,
                'You need to be a superuser to access this.'
            )
            return redirect('crashstats:home', settings.DEFAULT_PRODUCT)
        return view_func(request, *args, **kwargs)
    return inner


@superuser_required
def home(request, default_context=None):
    context = default_context or {}
    return render(request, 'manage/home.html', context)


@superuser_required
def featured_versions(request, default_context=None):
    context = default_context or {}

    products_api = CurrentProducts()
    products_api.cache_seconds = 0
    products = products_api.get()

    context['products'] = products['products']  # yuck!
    context['releases'] = {}
    now = datetime.date.today()
    for product_name in context['products']:
        context['releases'][product_name] = []
        for release in products['hits'][product_name]:
            start_date = datetime.datetime.strptime(
                release['start_date'],
                '%Y-%m-%d'
            ).date()
            if start_date > now:
                continue
            end_date = datetime.datetime.strptime(
                release['end_date'],
                '%Y-%m-%d'
            ).date()
            if end_date < now:
                continue
            context['releases'][product_name].append(release)

    return render(request, 'manage/featured_versions.html', context)


@superuser_required
@require_POST
def update_featured_versions(request):
    products_api = CurrentProducts()
    products = products_api.get()['products']

    data = {}
    for product in request.POST:
        if product in products:
            data[product] = request.POST.getlist(product)

    featured_api = ReleasesFeatured()
    if featured_api.put(**data):
        messages.success(
            request,
            'Featured versions successfully updated. '
            'Cache might take some time to update.'
        )

    url = reverse('manage:featured_versions')
    return redirect(url)


@superuser_required
def fields(request, default_context=None):
    context = default_context or {}
    return render(request, 'manage/fields.html', context)


@superuser_required
@json_view
def field_lookup(request):
    name = request.REQUEST.get('name', '').strip()
    if not name:
        return http.HttpResponseBadRequest("Missing 'name'")

    api = Field()
    return api.get(name=name)


@superuser_required
def skiplist(request, default_context=None):
    context = default_context or {}
    return render(request, 'manage/skiplist.html', context)


@superuser_required
@json_view
def skiplist_data(request):
    form = forms.SkipListForm(request.GET)
    form.fields['category'].required = False
    form.fields['rule'].required = False
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))
    category = form.cleaned_data['category']
    rule = form.cleaned_data['rule']

    api = SkipList()
    return api.get(category=category, rule=rule)


@superuser_required
@json_view
@require_POST
def skiplist_add(request):
    form = forms.SkipListForm(request.POST)
    if form.is_valid():
        category = form.cleaned_data['category']
        rule = form.cleaned_data['rule']
    else:
        return http.HttpResponseBadRequest(str(form.errors))

    api = SkipList()
    return api.post(category=category, rule=rule)


@superuser_required
@json_view
@require_POST
def skiplist_delete(request):
    form = forms.SkipListForm(request.POST)
    if form.is_valid():
        category = form.cleaned_data['category']
        rule = form.cleaned_data['rule']
    else:
        return http.HttpResponseBadRequest(str(form.errors))

    api = SkipList()
    return api.delete(category=category, rule=rule)


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
@transaction.commit_on_success
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
    context['user'] = user_
    return render(request, 'manage/user.html', context)


@transaction.commit_on_success
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
    measurements = []
    for label, value_type in (('API', 'classes'), ('URLS', 'urls')):
        all = cache.get('all_%s' % value_type) or []
        records = []
        for item in all:
            item = item[:220]
            data = {}
            data['times'] = {}
            data['times']['hits'] = cache.get('times_HIT_%s' % item, 0)
            data['times']['misses'] = cache.get('times_MISS_%s' % item, 0)
            data['times']['both'] = (
                data['times']['hits'] + data['times']['misses']
            )
            data['uses'] = {}
            data['uses']['hits'] = cache.get('uses_HIT_%s' % item, 0)
            data['uses']['misses'] = cache.get('uses_MISS_%s' % item, 0)
            data['uses']['both'] = (
                data['uses']['hits'] + data['uses']['misses']
            )
            records.append((item, data))
        measurements.append([label, value_type, records])
    context['measurements'] = measurements
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
            payload = list(
                parse_graphics_devices_iterable(
                    upload_form.cleaned_data['file']
                )
            )
            api = GraphicsDevices()
            result = api.post(json.dumps(payload))
            log(request.user, 'graphicsdevices.post', {'success': result})
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
            result = api.post(json.dumps(payload))
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
    context['all_uploads'] = (
        SymbolsUpload.objects.all()
        .order_by('-created')
    )
    return render(request, 'manage/symbols_uploads.html', context)


@superuser_required
def supersearch_fields(request):
    context = {}
    sorted_fields = sorted(
        SuperSearchFields().get().values(),
        key=lambda x: x['name'].lower()
    )
    context['fields'] = sorted_fields
    return render(request, 'manage/supersearch_fields.html', context)


@superuser_required
def supersearch_field(request):
    context = {}

    field_name = request.GET.get('name')

    if field_name:
        all_fields = SuperSearchFields().get()
        field_data = all_fields.get(field_name)

        if not field_data:
            return http.HttpResponseBadRequest(
                'The field "%s" does not exist' % field_name
            )
    else:
        full_name = request.GET.get('full_name')

        if full_name:
            if '.' not in full_name:
                name = full_name
                namespace = None
            else:
                namespace, name = full_name.rsplit('.', 1)
            field_data = {
                'in_database_name': name,
                'namespace': namespace,
            }
        else:
            field_data = {}

    context['field'] = field_data
    perms = Permission.objects.filter(content_type__model='').order_by('name')
    context['all_permissions'] = [
        'crashstats.' + x.codename for x in perms
    ]

    return render(request, 'manage/supersearch_field.html', context)


def _get_supersearch_field_data(source):
    form = forms.SuperSearchFieldForm(source)

    if not form.is_valid():
        return str(form.errors)

    return form.cleaned_data


@superuser_required
@require_POST
def supersearch_field_create(request):
    field_data = _get_supersearch_field_data(request.POST)

    if isinstance(field_data, basestring):
        return http.HttpResponseBadRequest(field_data)

    api = SuperSearchField()
    api.post(field_data)

    log(request.user, 'supersearch_field.post', field_data)

    # Refresh the cache for the fields service.
    SuperSearchFields().get(refresh_cache=True)

    # The API is using cache to get all fields by a specific namespace
    # for the whitelist lookup, clear that cache too.
    cache.delete('api_supersearch_fields_%s' % field_data['namespace'])

    return redirect(reverse('manage:supersearch_fields'))


@superuser_required
@require_POST
def supersearch_field_update(request):
    field_data = _get_supersearch_field_data(request.POST)

    if isinstance(field_data, basestring):
        return http.HttpResponseBadRequest(field_data)

    api = SuperSearchField()
    api.put(field_data)

    log(request.user, 'supersearch_field.put', field_data)

    # Refresh the cache for the fields service.
    SuperSearchFields().get(refresh_cache=True)

    return redirect(reverse('manage:supersearch_fields'))


@superuser_required
def supersearch_field_delete(request):
    field_name = request.GET.get('name')

    if not field_name:
        return http.HttpResponseBadRequest('A "name" is needed')

    api = SuperSearchField()
    api.delete(name=field_name)

    log(request.user, 'supersearch_field.delete', {'name': field_name})

    # Refresh the cache for the fields service.
    SuperSearchFields().get(refresh_cache=True)

    url = reverse('manage:supersearch_fields')
    return redirect(url)


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
    api = CurrentProducts()
    if request.method == 'POST':
        form = forms.ProductForm(
            request.POST,
            existing_products=api.get()['products']
        )
        if form.is_valid():
            api = CurrentProducts()
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
        form = forms.ProductForm(initial={
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
            action in ('supersearch_field.post', 'supersearch_field.put')
            and extra.get('name')
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
