import json
import re
import datetime
import inspect

from django import http
from django.shortcuts import render
from django.contrib.auth.models import Permission
from django.contrib.sites.requests import RequestSite
from django.core.urlresolvers import reverse
from django.conf import settings
from django import forms
from django.views.decorators.csrf import csrf_exempt
# explicit import because django.forms has an __all__
from django.forms.forms import DeclarativeFieldsMetaclass

from ratelimit.decorators import ratelimit

from socorro.lib import BadArgumentError, MissingArgumentError
from socorro.external.crashstorage_base import CrashIDNotFound

import crashstats
from crashstats.crashstats.decorators import track_api_pageview
from crashstats.crashstats import models
from crashstats.crashstats import utils
from crashstats.tokens.models import Token
from .cleaner import Cleaner


# List of all modules that contain models we want to expose.
MODELS_MODULES = (
    models,
    crashstats.tools.models,
    crashstats.supersearch.models,
    crashstats.symbols.models,
)


BAD_REQUEST_EXCEPTIONS = (
    BadArgumentError,
    MissingArgumentError,
    models.RequiredParameterError,
)

NOT_FOUND_EXCEPTIONS = (
    CrashIDNotFound,
)


class APIWhitelistError(Exception):
    pass


class MultipleStringField(forms.TypedMultipleChoiceField):
    """Field that do not validate if the field values are in self.choices"""

    def validate(self, value):
        """Nothing to do here"""
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'])


TYPE_MAP = {
    basestring: forms.CharField,
    list: MultipleStringField,
    datetime.date: forms.DateField,
    datetime.datetime: forms.DateTimeField,
    int: forms.IntegerField,
    bool: forms.BooleanField,
}


def fancy_init(self, model, *args, **kwargs):
    self.model = model
    self.__old_init__(*args, **kwargs)
    for parameter in model().get_annotated_params():
        required = parameter['required']
        name = parameter['name']

        if parameter['type'] not in TYPE_MAP:
            raise NotImplementedError(parameter['type'])
        field_class = TYPE_MAP[parameter['type']]
        self.fields[name] = field_class(required=required)


class FormWrapperMeta(DeclarativeFieldsMetaclass):
    def __new__(cls, name, bases, attrs):
        attrs['__old_init__'] = bases[0].__init__
        attrs['__init__'] = fancy_init
        return super(FormWrapperMeta, cls).__new__(cls, name, bases, attrs)


class FormWrapper(forms.Form):
    __metaclass__ = FormWrapperMeta

    def clean(self):
        cleaned_data = super(FormWrapper, self).clean()

        for field in self.fields:
            # Because the context for all of this is the API,
            # and we're using django forms there's a mismatch to how
            # boolean fields should be handled.
            # Django forms are meant for HTML forms. A key principle
            # functionality of a HTML form and a checkbox is that
            # if the user choses to NOT check a checkbox, the browser
            # will not send `mybool=false` or `mybool=''`. It will simply
            # not send anything and then the server has to assume the user
            # chose to NOT check it because it was offerend.
            # On a web API, however, the user doesn't use checkboxes.
            # He uses `?mybool=truthy` or `&mybool=falsy`.
            # Therefore, for our boolean fields, if the value is not
            # present at all, we have to assume it to be None.
            # That makes it possible to actually set `mybool=false`
            if isinstance(self.fields[field], forms.BooleanField):
                if field not in self.data:
                    self.cleaned_data[field] = None
        return cleaned_data


# Names of models we don't want to serve at all
BLACKLIST = (
    # only used for doing posts
    'Releases',
    # because it's only used for the admin
    'Field',
    'SuperSearchMissingFields',
    # because it's very sensitive and we don't want to expose it
    'Query',
    # because it's an internal thing only
    'GraphicsReport',
    'Priorityjob',
)


def has_permissions(user, permissions):
    for permission in permissions:
        if not user.has_perm(permission):
            return False
    return True


def is_valid_model_class(model):
    return (
        issubclass(model, models.SocorroMiddleware) and
        model is not models.SocorroMiddleware and
        model is not crashstats.supersearch.models.ESSocorroMiddleware
    )


@csrf_exempt
@ratelimit(
    key='ip',
    method=['GET', 'POST', 'PUT'],
    rate=utils.ratelimit_rate,
    block=True
)
@track_api_pageview
@utils.add_CORS_header  # must be before `utils.json_view`
@utils.json_view
def model_wrapper(request, model_name):
    if model_name in BLACKLIST:
        raise http.Http404("Don't know what you're talking about!")

    for source in MODELS_MODULES:
        try:
            model = getattr(source, model_name)
            break
        except AttributeError:
            pass
    else:
        raise http.Http404('no service called `%s`' % model_name)

    if not is_valid_model_class(model):
        raise http.Http404('no service called `%s`' % model_name)

    required_permissions = getattr(model(), 'API_REQUIRED_PERMISSIONS', None)
    if isinstance(required_permissions, basestring):
        required_permissions = [required_permissions]
    if (
        required_permissions and
        (
            not request.user.is_active or
            not has_permissions(request.user, required_permissions)
        )
    ):
        permission_names = []
        for permission in required_permissions:
            codename = permission.split('.', 1)[1]
            try:
                permission_names.append(
                    Permission.objects.get(
                        codename=codename
                    ).name
                )
            except Permission.DoesNotExist:
                permission_names.append(codename)
        # you're not allowed to use this model
        return http.JsonResponse({
            'error': "Use of this endpoint requires the '%s' permission" % (
                ', '.join(permission_names),
            )
        }, status=403)

    # it being set to None means it's been deliberately disabled
    if getattr(model, 'API_WHITELIST', False) is False:
        raise APIWhitelistError('No API_WHITELIST defined for %r' % model)

    instance = model()

    # Any additional headers we intend to set on the response
    headers = {}

    # Certain models need to know who the user is to be able to
    # internally use that to determine its output.
    instance.api_user = request.user

    if request.method == 'POST':
        function = instance.post
    else:
        function = instance.get
    if not function:
        return http.HttpResponseNotAllowed([request.method])

    # assume first that it won't need a binary response
    binary_response = False

    request_data = request.method == 'GET' and request.GET or request.POST
    form = FormWrapper(model, request_data)
    if form.is_valid():
        try:
            result = function(**form.cleaned_data)
        except ValueError as e:
            if (
                # built in json module ValueError
                'No JSON object could be decoded' in e or
                # ujson module ValueError
                'Expected object or value' in e
            ):
                return http.HttpResponseBadRequest(
                    json.dumps({'error': 'Not a valid JSON response'}),
                    content_type='application/json; charset=UTF-8'
                )
            raise
        except NOT_FOUND_EXCEPTIONS as exception:
            return http.HttpResponseNotFound(
                json.dumps({'error': unicode(exception)}),
                content_type='application/json; charset=UTF-8'
            )
        except BAD_REQUEST_EXCEPTIONS as exception:
            return http.HttpResponseBadRequest(
                json.dumps({'error': unicode(exception)}),
                content_type='application/json; charset=UTF-8'
            )

        # Some models allows to return a binary reponse. It does so based on
        # the models `BINARY_RESPONSE` dict in which all keys and values
        # need to be in the valid query. For example, if the query is
        # `?foo=bar&other=thing&bar=baz` and the `BINARY_RESPONSE` dict is
        # exactly: {'foo': 'bar', 'bar': 'baz'} it will return a binary
        # response with content type `application/octet-stream`.
        for key, value in model.API_BINARY_RESPONSE.items():
            if form.cleaned_data.get(key) == value:
                binary_response = True
            else:
                binary_response = False
                break

        if binary_response:
            # if you don't have all required permissions, you'll get a 403
            required_permissions = model.API_BINARY_PERMISSIONS
            if isinstance(required_permissions, basestring):
                required_permissions = [required_permissions]
            if (
                required_permissions and
                not has_permissions(request.user, required_permissions)
            ):
                permission_names = []
                for permission in required_permissions:
                    codename = permission.split('.', 1)[1]
                    try:
                        permission_names.append(
                            Permission.objects.get(
                                codename=codename
                            ).name
                        )
                    except Permission.DoesNotExist:
                        permission_names.append(codename)
                # you're not allowed to get the binary response
                return http.HttpResponseForbidden(
                    "Binary response requires the '%s' permission\n" %
                    (', '.join(permission_names))
                )

        elif not request.user.has_perm('crashstats.view_pii'):
            clean_scrub = getattr(model, 'API_CLEAN_SCRUB', None)

            if callable(model.API_WHITELIST):
                whitelist = model.API_WHITELIST()
            else:
                whitelist = model.API_WHITELIST

            if result and whitelist:
                cleaner = Cleaner(
                    whitelist,
                    clean_scrub=clean_scrub,
                    # if True, uses warnings.warn() to show fields
                    # not whitelisted
                    debug=settings.DEBUG,
                )
                cleaner.start(result)

    else:
        # custom override of the status code
        return {'errors': dict(form.errors)}, 400

    if binary_response:
        assert model.API_BINARY_FILENAME, 'No API_BINARY_FILENAME set on model'
        response = http.HttpResponse(
            result,
            content_type='application/octet-stream'
        )
        filename = model.API_BINARY_FILENAME % form.cleaned_data
        response['Content-Disposition'] = (
            'attachment; filename="%s"' % filename
        )
        return response

    if (
        getattr(model, 'deprecation_warning', False)
    ):
        if isinstance(result, dict):
            result['DEPRECATION_WARNING'] = model.deprecation_warning
        # If you return a tuple of two dicts, the second one becomes
        # the extra headers.
        # return result, {
        headers['DEPRECATION-WARNING'] = (
            model.deprecation_warning.replace('\n', ' ')
        )

    if model.cache_seconds:
        # We can set a Cache-Control header.
        # We say 'private' because the content can depend on the user
        # and we don't want the response to be collected in HTTP proxies
        # by mistake.
        headers['Cache-Control'] = 'private, max-age={}'.format(
            model.cache_seconds,
        )

    return result, headers


def documentation(request):
    endpoints = []

    all_models = []
    unique_model_names = set()
    for source in MODELS_MODULES:
        for name, value in inspect.getmembers(source):
            if name in unique_model_names:
                # model potentially in multiple modules
                continue
            if inspect.isclass(value):
                all_models.append(value)
                unique_model_names.add(name)

    for model in all_models:
        try:
            if not is_valid_model_class(model):
                continue
            if model.__name__ in BLACKLIST:
                continue
        except TypeError:
            # most likely a builtin class or something
            continue

        model_inst = model()
        if (
            model_inst.API_REQUIRED_PERMISSIONS and
            not has_permissions(
                request.user,
                model_inst.API_REQUIRED_PERMISSIONS
            )
        ):
            continue
        endpoints.append(_describe_model(model))

    base_url = (
        '%s://%s' % (request.is_secure() and 'https' or 'http',
                     RequestSite(request).domain)
    )
    if request.user.is_active:
        your_tokens = Token.objects.active().filter(user=request.user)
    else:
        your_tokens = Token.objects.none()
    context = {
        'endpoints': endpoints,
        'base_url': base_url,
        'count_tokens': your_tokens.count()
    }
    return render(request, 'api/documentation.html', context)


def _describe_model(model):
    model_inst = model()
    params = list(model_inst.get_annotated_params())
    params.sort(key=lambda x: (not x['required'], x['name']))
    methods = []
    if model.get:
        methods.append('GET')
    elif model.post:
        methods.append('POST')

    docstring = model.__doc__
    if docstring:
        docstring = dedent_left(docstring.rstrip(), 4)

    required_permissions = []
    if model_inst.API_REQUIRED_PERMISSIONS:
        permissions = model_inst.API_REQUIRED_PERMISSIONS
        if isinstance(permissions, basestring):
            permissions = [permissions]
        for permission in permissions:
            codename = permission.split('.', 1)[1]
            required_permissions.append(
                Permission.objects.get(codename=codename).name
            )

    data = {
        'name': model.__name__,
        'url': reverse('api:model_wrapper', args=(model.__name__,)),
        'parameters': params,
        'defaults': getattr(model, 'defaults', {}),
        'methods': methods,
        'docstring': docstring,
        'required_permissions': required_permissions,
        'deprecation_warning': getattr(model, 'deprecation_warning', None),
    }
    return data


def dedent_left(text, spaces):
    """
    If the string is:
        '   One\n'
        '     Two\n'
        'Three\n'

    And you set @spaces=2
    Then return this:
        ' One\n'
        '   Two\n'
        'Three\n'
    """
    lines = []
    regex = re.compile('^\s{%s}' % spaces)
    for line in text.splitlines():
        line = regex.sub('', line)
        lines.append(line)
    return '\n'.join(lines)
