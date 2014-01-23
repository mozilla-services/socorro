import datetime
import functools

from django import http
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User, Group, Permission
from django.core.cache import cache
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404

from crashstats.crashstats.models import (
    CurrentProducts,
    ReleasesFeatured,
    Field,
    SkipList
)
from crashstats.crashstats.utils import json_view
from . import forms


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
            return redirect('crashstats.home', settings.DEFAULT_PRODUCT)
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

    count = users_.count()
    user_items = []
    batch_size = getattr(settings, 'USERS_ADMIN_BATCH_SIZE', 10)
    for user in users_[:batch_size]:
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
    return {'users': user_items, 'count': count}


@json_view
@superuser_required
def user(request, id):
    context = {}
    user_ = get_object_or_404(User, id=id)
    if request.method == 'POST':
        form = forms.EditUserForm(request.POST, instance=user_)
        if form.is_valid():
            form.save()
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


@superuser_required
def groups(request):
    context = {}
    if request.method == 'POST':
        if request.POST.get('delete'):
            group = get_object_or_404(Group, pk=request.POST['delete'])
            group.delete()
            messages.success(
                request,
                'Group deleted.'
            )
            return redirect('manage:groups')
        form = forms.GroupForm(request.POST)
        if form.is_valid():
            form.save()
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
        form = forms.GroupForm(request.POST, instance=group_)
        if form.is_valid():
            form.save()
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
