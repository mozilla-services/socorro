import re
import datetime

from django import http
from django.shortcuts import render
from django.contrib.sites.models import RequestSite
from django.core.urlresolvers import reverse
from django.conf import settings
from django import forms

from ratelimit.decorators import ratelimit
from waffle.decorators import waffle_switch

from crashstats.crashstats import models
from crashstats.crashstats import utils
from .cleaner import Cleaner


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
    for parameter in model.get_annotated_params():
        required = parameter['required']
        name = parameter['name']

        if parameter['type'] not in TYPE_MAP:
            raise NotImplementedError(parameter['type'])
        field_class = TYPE_MAP[parameter['type']]
        self.fields[name] = field_class(required=required)


class FormWrapperMeta(forms.Form.__metaclass__):
    def __new__(cls, name, bases, attrs):
        attrs['__old_init__'] = bases[0].__init__
        attrs['__init__'] = fancy_init
        return super(FormWrapperMeta, cls).__new__(cls, name, bases, attrs)


class FormWrapper(forms.Form):
    __metaclass__ = FormWrapperMeta


# Names of models we don't want to serve at all
BLACKLIST = (
    # empty at the moment
)


@waffle_switch('app_api_all')
@ratelimit(method=['GET', 'POST', 'PUT'], rate='10/m')
@utils.json_view
def model_wrapper(request, model_name):
    if model_name in BLACKLIST:
        raise http.Http404("Don't know what you're talking about!")
    try:
        model = getattr(models, model_name)
    except AttributeError:
        raise http.Http404('no model called `%s`' % model_name)

    # XXX use RatelimitMiddleware instead of this in case
    # we ratelimit multiple views
    if getattr(request, 'limited', False):
        # http://tools.ietf.org/html/rfc6585#page-3
        return http.HttpResponse('Too Many Requests', status=429)

    instance = model()
    if request.method == 'POST':
        function = instance.post
    else:
        function = instance.get

    form = FormWrapper(model, request.REQUEST)
    if form.is_valid():
        try:
            result = function(**form.cleaned_data)
        except models.BadStatusCodeError as e:
            try:
                error_code = int(str(e).split(':')[0].strip())
                if error_code >= 400 and error_code < 500:
                    return http.HttpResponse(e, status=error_code)
                if error_code >= 500:
                    return http.HttpResponse(e, status=424)
            except Exception:
                # that means we can't assume that the BadStatusCodeError
                # has a typically formatted error message
                pass
            raise
        except ValueError as e:
            if 'No JSON object could be decoded' in e:
                return http.HttpResponse(
                    'Not a valid JSON response',
                    status=400
                )
            raise

        # it being set to None means it's been deliberately disabled
        if getattr(model, 'API_WHITELIST', -1) == -1:
            raise APIWhitelistError('No API_WHITELIST defined for %r' % model)

        clean_scrub = getattr(model, 'API_CLEAN_SCRUB', None)
        if model.API_WHITELIST:
            cleaner = Cleaner(
                model.API_WHITELIST,
                clean_scrub=clean_scrub,
                # if True, uses warnings.warn() to show fields not whitelisted
                debug=settings.DEBUG,
            )
            cleaner.start(result)

    else:
        result = {'errors': dict(form.errors)}

    return result


@waffle_switch('app_api_all')
def documentation(request):
    endpoints = [
    ]

    for name in dir(models):
        model = getattr(models, name)
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
        endpoints.append(_describe_model(model))

    base_url = (
        '%s://%s' % (request.is_secure() and 'https' or 'http',
                     RequestSite(request).domain)
    )
    data = {
        'endpoints': endpoints,
        'base_url': base_url,
    }
    return render(request, 'api/documentation.html', data)


def _describe_model(model):
    params = list(model.get_annotated_params())
    params.sort(key=lambda x: (not x['required'], x['name']))
    methods = []
    if model.get:
        methods.append('GET')
    elif models.post:
        methods.append('POST')

    docstring = model.__doc__
    if docstring:
        docstring = dedent_left(docstring.rstrip(), 4)
    data = {
        'name': model.__name__,
        'url': reverse('api:model_wrapper', args=(model.__name__,)),
        'parameters': params,
        'defaults': getattr(model, 'defaults', {}),
        'methods': methods,
        'docstring': docstring,
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
