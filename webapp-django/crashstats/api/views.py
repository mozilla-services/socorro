import json
import re
import datetime

from django import http
from django.shortcuts import render
from django.contrib.auth.models import Permission
from django.contrib.sites.models import RequestSite
from django.core.urlresolvers import reverse
from django.conf import settings
from django import forms
# explicit import because django.forms has an __all__
from django.forms.forms import DeclarativeFieldsMetaclass

from ratelimit.decorators import ratelimit
from waffle.decorators import waffle_switch

import crashstats.supersearch.models
from crashstats.crashstats import models
from crashstats.crashstats import utils
from crashstats.tokens.models import Token
from .cleaner import Cleaner


# List of all modules that contain models we want to expose.
MODELS_MODULES = (
    models,
    crashstats.supersearch.models,
)


# See http://www.iana.org/assignments/http-status-codes
REASON_PHRASES = {
    100: 'CONTINUE',
    101: 'SWITCHING PROTOCOLS',
    102: 'PROCESSING',
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    207: 'MULTI-STATUS',
    208: 'ALREADY REPORTED',
    226: 'IM USED',
    300: 'MULTIPLE CHOICES',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    306: 'RESERVED',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    402: 'PAYMENT REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    418: "I'M A TEAPOT",
    422: 'UNPROCESSABLE ENTITY',
    423: 'LOCKED',
    424: 'FAILED DEPENDENCY',
    426: 'UPGRADE REQUIRED',
    428: 'PRECONDITION REQUIRED',
    429: 'TOO MANY REQUESTS',
    431: 'REQUEST HEADER FIELDS TOO LARGE',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
    506: 'VARIANT ALSO NEGOTIATES',
    507: 'INSUFFICIENT STORAGE',
    508: 'LOOP DETECTED',
    510: 'NOT EXTENDED',
    511: 'NETWORK AUTHENTICATION REQUIRED',
}


class APIWhitelistError(Exception):
    pass


class MultipleStringField(forms.TypedMultipleChoiceField):
    """Field that do not validate if the field values are in self.choices"""

    def to_python(self, value):
        """Override checking method"""
        return map(self.coerce, value)

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


# Names of models we don't want to serve at all
BLACKLIST = (
    # not because it's sensitive but because it's only used for writes
    'ReleasesFeatured',
    # because it's only used for the admin
    'Field',
    'SuperSearchField',
    'SuperSearchMissingFields',
    # because it's very sensitive and we don't want to expose it
    'Query',
    # because it's an internal thing only
    'SuperSearchFields',
)


def _skip_ratelimit(request):
    return request.user.is_authenticated()


def has_permissions(user, permissions):
    for permission in permissions:
        if not user.has_perm(permission):
            return False
    return True


@waffle_switch('app_api_all')
@ratelimit(
    method=['GET', 'POST', 'PUT'],
    rate='10/m',
    skip_if=_skip_ratelimit
)
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
        raise http.Http404('no model called `%s`' % model_name)

    required_permissions = getattr(model(), 'API_REQUIRED_PERMISSIONS', None)
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
        # you're not allowed to use this model
        return http.HttpResponseForbidden(
            "Use of this endpoint requires the '%s' permission\n" %
            (', '.join(permission_names))
        )

    # XXX use RatelimitMiddleware instead of this in case
    # we ratelimit multiple views
    if getattr(request, 'limited', False):
        # http://tools.ietf.org/html/rfc6585#page-3
        return http.HttpResponse('Too Many Requests', status=429)

    # it being set to None means it's been deliberately disabled
    if getattr(model, 'API_WHITELIST', False) is False:
        raise APIWhitelistError('No API_WHITELIST defined for %r' % model)

    instance = model()
    if request.method == 'POST':
        function = instance.post
    else:
        function = instance.get

    # assume first that it won't need a binary response
    binary_response = False

    form = FormWrapper(model, request.REQUEST)
    if form.is_valid():
        try:
            result = function(**form.cleaned_data)
        except models.BadStatusCodeError as e:
            error_code = e.status
            message = e.message
            if error_code >= 400 and error_code < 500:
                # if the error message looks like JSON,
                # carry that forward in the response
                try:
                    json.loads(message)
                    return http.HttpResponse(
                        message,
                        status=error_code,
                        mimetype='application/json; charset=UTF-8'
                    )
                except ValueError:
                    # The error from the middleware was not a JSON error.
                    # Not much more we can do.
                    reason = REASON_PHRASES.get(
                        error_code,
                        'UNKNOWN STATUS CODE'
                    )
                    return http.HttpResponse(reason, status=error_code)
            if error_code >= 500:
                # special case
                reason = REASON_PHRASES[424]
                return http.HttpResponse(
                    reason,
                    status=424,
                    mimetype='text/plain'
                )
            raise
        except ValueError as e:
            if (
                # built in json module ValueError
                'No JSON object could be decoded' in e or
                # ujson module ValueError
                'Expected object or value' in e
            ):
                return http.HttpResponse(
                    'Not a valid JSON response',
                    status=400
                )
            raise

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
            if result and model.API_WHITELIST:
                cleaner = Cleaner(
                    model.API_WHITELIST,
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

    return result


@waffle_switch('app_api_all')
def documentation(request):
    endpoints = [
    ]

    all_models = []
    for source in MODELS_MODULES:
        all_models += [getattr(source, x) for x in dir(source)]

    for model in all_models:
        try:
            if not issubclass(model, models.SocorroMiddleware):
                continue
            if model is models.SocorroMiddleware:
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
    if request.user.is_authenticated():
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
