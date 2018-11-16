import datetime
import inspect
import json
import re

from django import http
from django import forms
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.sites.requests import RequestSite
from django.core.urlresolvers import reverse
# explicit import because django.forms has an __all__
from django.forms.forms import DeclarativeFieldsMetaclass
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from ratelimit.decorators import ratelimit
import six

from crashstats.api.cleaner import Cleaner
from crashstats.crashstats import models
from crashstats.crashstats import utils
from crashstats.crashstats.decorators import track_api_pageview, pass_default_context
from crashstats.supersearch import models as supersearch_models
from crashstats.tokens import models as tokens_models
from crashstats.tools import models as tools_models
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib import BadArgumentError, MissingArgumentError
from socorro.lib.ooid import is_crash_id_valid


# List of all modules that contain models we want to expose.
MODELS_MODULES = (
    models,
    tools_models,
    supersearch_models,
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
    six.text_type: forms.CharField,
    list: MultipleStringField,
    datetime.date: forms.DateField,
    datetime.datetime: forms.DateTimeField,
    int: forms.IntegerField,
    bool: forms.BooleanField,
}
if six.PY2:
    # NOTE(willkg): In python 2, we need to additionally add str which is a
    # text type
    TYPE_MAP[str] = forms.CharField


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


@six.add_metaclass(FormWrapperMeta)
class FormWrapper(forms.Form):
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
    # because it's only used for the admin
    'Field',
    'SuperSearchMissingFields',
    # because it's very sensitive and we don't want to expose it
    'Query',
    # because it's an internal thing only
    'Priorityjob',
    'Products',
    'TelemetryCrash',
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
        model is not supersearch_models.ESSocorroMiddleware
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

    model = None

    for source in MODELS_MODULES:
        try:
            model = getattr(source, model_name)
            break
        except AttributeError:
            pass
        try:
            model = getattr(source, model_name + 'Middleware')
        except AttributeError:
            pass

    if model is None or not is_valid_model_class(model):
        raise http.Http404('no service called `%s`' % model_name)

    required_permissions = getattr(model(), 'API_REQUIRED_PERMISSIONS', None)
    if isinstance(required_permissions, six.string_types):
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
                permission_names.append(Permission.objects.get(codename=codename).name)
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
            if 'No JSON object could be decoded' in e:
                return http.HttpResponseBadRequest(
                    json.dumps({'error': 'Not a valid JSON response'}),
                    content_type='application/json; charset=UTF-8'
                )
            raise
        except NOT_FOUND_EXCEPTIONS as exception:
            return http.HttpResponseNotFound(
                json.dumps({'error': ('%s: %s' % (type(exception).__name__, exception))}),
                content_type='application/json; charset=UTF-8'
            )
        except BAD_REQUEST_EXCEPTIONS as exception:
            return http.HttpResponseBadRequest(
                json.dumps({'error': ('%s: %s' % (type(exception).__name__, exception))}),
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
            if isinstance(required_permissions, six.string_types):
                required_permissions = [required_permissions]
            if required_permissions and not has_permissions(request.user, required_permissions):
                permission_names = []
                for permission in required_permissions:
                    codename = permission.split('.', 1)[1]
                    try:
                        permission_names.append(Permission.objects.get(codename=codename).name)
                    except Permission.DoesNotExist:
                        permission_names.append(codename)
                # you're not allowed to get the binary response
                return http.HttpResponseForbidden(
                    "Binary response requires the '%s' permission\n" %
                    (', '.join(permission_names))
                )

        elif not request.user.has_perm('crashstats.view_pii'):
            if callable(model.API_WHITELIST):
                whitelist = model.API_WHITELIST()
            else:
                whitelist = model.API_WHITELIST

            if result and whitelist:
                cleaner = Cleaner(
                    whitelist,
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
        response = http.HttpResponse(result, content_type='application/octet-stream')
        filename = model.API_BINARY_FILENAME % form.cleaned_data
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response

    if getattr(model, 'deprecation_warning', False):
        if isinstance(result, dict):
            result['DEPRECATION_WARNING'] = model.deprecation_warning
        # If you return a tuple of two dicts, the second one becomes
        # the extra headers.
        # return result, {
        headers['DEPRECATION-WARNING'] = model.deprecation_warning.replace('\n', ' ')

    if model.cache_seconds:
        # We can set a Cache-Control header.
        # We say 'private' because the content can depend on the user
        # and we don't want the response to be collected in HTTP proxies
        # by mistake.
        headers['Cache-Control'] = 'private, max-age={}'.format(model.cache_seconds)

    return result, headers


@pass_default_context
def documentation(request, default_context=None):
    context = default_context or {}

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
        model_name = model.__name__
        if model_name.endswith('Middleware'):
            model_name = model_name[:-10]

        try:
            if not is_valid_model_class(model):
                continue
            if model_name in BLACKLIST:
                continue
        except TypeError:
            # most likely a builtin class or something
            continue

        model_inst = model()
        if (
            model_inst.API_REQUIRED_PERMISSIONS and
            not has_permissions(request.user, model_inst.API_REQUIRED_PERMISSIONS)
        ):
            continue
        endpoints.append(_describe_model(model_name, model))

    endpoints.sort(key=lambda ep: ep['name'])

    base_url = (
        '%s://%s' % (request.is_secure() and 'https' or 'http',
                     RequestSite(request).domain)
    )
    if request.user.is_active:
        your_tokens = tokens_models.Token.objects.active().filter(user=request.user)
    else:
        your_tokens = tokens_models.Token.objects.none()
    context.update({
        'endpoints': endpoints,
        'base_url': base_url,
        'count_tokens': your_tokens.count()
    })
    return render(request, 'api/documentation.html', context)


def _describe_model(model_name, model):
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
        if isinstance(permissions, six.string_types):
            permissions = [permissions]
        for permission in permissions:
            codename = permission.split('.', 1)[1]
            required_permissions.append(Permission.objects.get(codename=codename).name)

    data = {
        'name': model_name,
        'url': reverse('api:model_wrapper', args=(model_name,)),
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
    regex = re.compile(r'^\s{%s}' % spaces)
    for line in text.splitlines():
        line = regex.sub('', line)
        lines.append(line)
    return '\n'.join(lines)


@csrf_exempt
@ratelimit(
    key='ip',
    method=['GET'],
    rate=utils.ratelimit_rate,
    block=True
)
@utils.add_CORS_header
@utils.json_view
def crash_verify(request):
    """Verifies crash data in crash data destinations"""
    crash_id = request.GET.get('crash_id', None)

    if not crash_id or not is_crash_id_valid(crash_id):
        return http.JsonResponse({'error': 'unknown crash id'}, status=400)

    data = {
        'uuid': crash_id
    }

    # Check S3 crash bucket for raw and processed crash data
    raw_api = models.RawCrash()
    try:
        raw_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_raw_crash = True
    except CrashIDNotFound:
        has_raw_crash = False
    data['s3_raw_crash'] = has_raw_crash

    processed_api = models.ProcessedCrash()
    try:
        processed_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_processed_crash = True
    except CrashIDNotFound:
        has_processed_crash = False
    data['s3_processed_crash'] = has_processed_crash

    # Check Elasticsearch for crash data
    supersearch_api = supersearch_models.SuperSearch()
    params = {
        '_columns': ['uuid'],
        '_results_number': 1,
        'uuid': crash_id,
        'dont_cache': True,
        'refresh_cache': True
    }
    results = supersearch_api.get(**params)
    data['elasticsearch_crash'] = (
        results['total'] == 1 and
        results['hits'][0]['uuid'] == crash_id
    )

    # Check S3 telemetry bucket for crash data
    telemetry_api = models.TelemetryCrash()
    try:
        telemetry_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_telemetry_crash = True
    except CrashIDNotFound:
        has_telemetry_crash = False
    data['s3_telemetry_crash'] = has_telemetry_crash

    return http.HttpResponse(json.dumps(data), content_type='application/json')
