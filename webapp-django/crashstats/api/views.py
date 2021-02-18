# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from functools import wraps
import inspect
import json
import re

from ratelimit.decorators import ratelimit
from session_csrf import anonymous_csrf_exempt

from django import http
from django import forms
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.sites.requests import RequestSite
from django.core.validators import ProhibitNullCharactersValidator
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

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
MODELS_MODULES = (models, tools_models, supersearch_models)


BAD_REQUEST_EXCEPTIONS = (
    BadArgumentError,
    MissingArgumentError,
    models.RequiredParameterError,
)

NOT_FOUND_EXCEPTIONS = (CrashIDNotFound,)


class MultipleStringField(forms.TypedMultipleChoiceField):
    """
    Field that does not validate if the field values are in self.choices

    Validators are run on each item in the list, rather than against the whole input,
    like other Django fields.
    """

    default_validators = [ProhibitNullCharactersValidator()]

    def valid_value(self, value):
        """
        Run validators on each item in the list.

        The TypedMultipleChoiceField.valid_value method checks that
        the string is in self.choices, and this version explictly skips that check.
        """
        self.run_validators(value)
        return True


TYPE_MAP = {
    str: forms.CharField,
    list: MultipleStringField,
    datetime.date: forms.DateField,
    # NOTE: Not used in any API models
    datetime.datetime: forms.DateTimeField,
    int: forms.IntegerField,
    # NOTE: Not used in any API models
    bool: forms.NullBooleanField,
}


class MiddlewareModelForm(forms.Form):
    """Generate a Form from a SocorroMiddleware-derived model class."""

    def __init__(self, model, *args, **kwargs):
        self.model = model
        super().__init__(*args, **kwargs)

        # Populate the form fields
        for parameter in model().get_annotated_params():
            required = parameter["required"]
            name = parameter["name"]
            field_class = TYPE_MAP[parameter["type"]]
            self.fields[name] = field_class(required=required)


# Names of models we don't want to serve at all
API_DONT_SERVE_LIST = (
    # because it's only used for the admin
    "Field",
    "SuperSearchMissingFields",
    # because it's very sensitive and we don't want to expose it
    "Query",
    # because it's an internal thing only
    "PriorityJob",
    "TelemetryCrash",
)


def is_valid_model_class(model):
    return (
        isinstance(model, type)
        and issubclass(model, models.SocorroMiddleware)
        and model is not models.SocorroMiddleware
        and model is not supersearch_models.ESSocorroMiddleware
    )


def clear_empty_session(fun):
    """Clears empty sessions so they don't persist"""

    @wraps(fun)
    def _clear_empty_session(request, *args, **kwargs):
        # Run the function
        ret = fun(request, *args, **kwargs)

        # Clear the session if nothing was saved to it
        session_keys = [
            key for key in request.session.keys() if not key.startswith("_auth_user")
        ]
        if not session_keys:
            request.session.clear()
            request.session.flush()
        return ret

    return _clear_empty_session


def no_csrf_i_mean_it(fun):
    """Removes any csrf bits from request

    This removes any csrf bookkeeping by middleware from the request so that it doesn't
    get persisted in cookies and elsewhere.

    Note: If we ever change ANON_ALWAYS setting for django-session-csrf, then we can nix
    this. Otherwise django-session-csrf *always* creates an anoncsrf cookie regardless
    of the existence of the anonymous_csrf_exempt decorator.

    """

    @wraps(fun)
    def _no_csrf(request, *args, **kwargs):
        ret = fun(request, *args, **kwargs)
        # Remove any csrf bits from Django or django-session-csrf so they don't persist
        if hasattr(request, "_anon_csrf_key"):
            del request._anon_csrf_key
        return ret

    return _no_csrf


@anonymous_csrf_exempt
@csrf_exempt
@no_csrf_i_mean_it
@clear_empty_session
@ratelimit(
    key="ip", method=["GET", "POST", "PUT"], rate=utils.ratelimit_rate, block=True
)
@track_api_pageview
@utils.add_CORS_header  # must be before `utils.json_view`
@utils.json_view
def model_wrapper(request, model_name):
    if model_name in API_DONT_SERVE_LIST:
        raise http.Http404("Don't know what you're talking about!")

    model = None

    for source in MODELS_MODULES:
        try:
            model = getattr(source, model_name)
            break
        except AttributeError:
            pass
        try:
            model = getattr(source, model_name + "Middleware")
        except AttributeError:
            pass

    if model is None or not is_valid_model_class(model):
        raise http.Http404("no service called `%s`" % model_name)

    required_permissions = getattr(model(), "API_REQUIRED_PERMISSIONS", None)
    if required_permissions and (
        not request.user.is_active or not request.user.has_perms(required_permissions)
    ):
        permission_names = []
        for permission in required_permissions:
            codename = permission.split(".", 1)[1]
            try:
                permission_names.append(Permission.objects.get(codename=codename).name)
            except Permission.DoesNotExist:
                permission_names.append(codename)
        # you're not allowed to use this model
        return http.JsonResponse(
            {
                "error": "Use of this endpoint requires the '%s' permission"
                % (", ".join(permission_names),)
            },
            status=403,
        )

    instance = model()

    # Any additional headers we intend to set on the response
    headers = {}

    # Certain models need to know who the user is to be able to
    # internally use that to determine its output.
    instance.api_user = request.user

    if request.method == "POST":
        function = instance.post
    else:
        function = instance.get
    if not function:
        return http.HttpResponseNotAllowed([request.method])

    # assume first that it won't need a binary response
    binary_response = False

    request_data = request.method == "GET" and request.GET or request.POST
    form = MiddlewareModelForm(model, request_data)
    if form.is_valid():
        try:
            result = function(**form.cleaned_data)
        except NOT_FOUND_EXCEPTIONS as exception:
            return http.HttpResponseNotFound(
                json.dumps(
                    {"error": ("%s: %s" % (type(exception).__name__, exception))}
                ),
                content_type="application/json; charset=UTF-8",
            )
        except BAD_REQUEST_EXCEPTIONS as exception:
            return http.HttpResponseBadRequest(
                json.dumps(
                    {"error": ("%s: %s" % (type(exception).__name__, exception))}
                ),
                content_type="application/json; charset=UTF-8",
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
            if required_permissions and not request.user.has_perms(
                required_permissions
            ):
                permission_names = []
                for permission in required_permissions:
                    codename = permission.split(".", 1)[1]
                    try:
                        permission_names.append(
                            Permission.objects.get(codename=codename).name
                        )
                    except Permission.DoesNotExist:
                        permission_names.append(codename)
                # you're not allowed to get the binary response
                return http.HttpResponseForbidden(
                    "Binary response requires the '%s' permission\n"
                    % (", ".join(permission_names))
                )

        elif not request.user.has_perm("crashstats.view_pii"):
            if callable(model.API_ALLOWLIST):
                allowlist = model.API_ALLOWLIST()
            else:
                allowlist = model.API_ALLOWLIST

            if result and allowlist:
                cleaner = Cleaner(
                    allowlist,
                    # if True, uses warnings.warn() to show fields
                    # not allowlisted
                    debug=settings.DEBUG,
                )
                cleaner.start(result)

    else:
        # custom override of the status code
        return {"errors": dict(form.errors)}, 400

    if binary_response:
        assert model.API_BINARY_FILENAME, "No API_BINARY_FILENAME set on model"
        response = http.HttpResponse(result, content_type="application/octet-stream")
        filename = model.API_BINARY_FILENAME % form.cleaned_data
        response["Content-Disposition"] = 'attachment; filename="%s"' % filename
        return response

    if getattr(model, "deprecation_warning", False):
        if isinstance(result, dict):
            result["DEPRECATION_WARNING"] = model.deprecation_warning
        headers["DEPRECATION-WARNING"] = model.deprecation_warning.replace("\n", " ")

    if model.cache_seconds:
        # We can set a Cache-Control header.
        # We say 'private' because the content can depend on the user
        # and we don't want the response to be collected in HTTP proxies
        # by mistake.
        headers["Cache-Control"] = f"private, max-age={model.cache_seconds}"

    return result, headers


def api_models_and_names():
    """Return list of (model class, model name) pairs."""
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

    models_with_names = []
    for model in all_models:
        model_name = model.__name__
        if model_name.endswith("Middleware"):
            model_name = model_name[:-10]

        if not is_valid_model_class(model):
            continue
        if model_name in API_DONT_SERVE_LIST:
            continue

        models_with_names.append((model, model_name))
    models_with_names.sort(key=lambda pair: pair[1])
    return models_with_names


@pass_default_context
def documentation(request, default_context=None):
    context = default_context or {}

    # Include models that the user is allowed to access
    endpoints = []
    for model, model_name in api_models_and_names():
        model_inst = model()
        if model_inst.API_REQUIRED_PERMISSIONS and not request.user.has_perms(
            model_inst.API_REQUIRED_PERMISSIONS
        ):
            continue
        endpoints.append(_describe_model(model_name, model))

    base_url = "%s://%s" % (
        request.is_secure() and "https" or "http",
        RequestSite(request).domain,
    )
    if request.user.is_active:
        your_tokens = tokens_models.Token.objects.active().filter(user=request.user)
    else:
        your_tokens = tokens_models.Token.objects.none()
    context.update(
        {
            "endpoints": endpoints,
            "base_url": base_url,
            "count_tokens": your_tokens.count(),
        }
    )
    return render(request, "api/documentation.html", context)


def _describe_model(model_name, model):
    model_inst = model()
    params = list(model_inst.get_annotated_params())
    params.sort(key=lambda x: (not x["required"], x["name"]))
    methods = []
    if model.get:
        methods.append("GET")
    elif model.post:
        methods.append("POST")

    help_text = model.HELP_TEXT
    if help_text:
        help_text = dedent_left(help_text.rstrip(), 4)

    required_permissions = []
    if model_inst.API_REQUIRED_PERMISSIONS:
        for permission in model_inst.API_REQUIRED_PERMISSIONS:
            codename = permission.split(".", 1)[1]
            required_permissions.append(Permission.objects.get(codename=codename).name)

    data = {
        "name": model_name,
        "url": reverse("api:model_wrapper", args=(model_name,)),
        "parameters": params,
        "defaults": getattr(model, "defaults", {}),
        "methods": methods,
        "help_text": help_text,
        "required_permissions": required_permissions,
        "deprecation_warning": getattr(model, "deprecation_warning", None),
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
    regex = re.compile(r"^\s{%s}" % spaces)
    for line in text.splitlines():
        line = regex.sub("", line)
        lines.append(line)
    return "\n".join(lines)


@anonymous_csrf_exempt
@csrf_exempt
@ratelimit(key="ip", method=["GET"], rate=utils.ratelimit_rate, block=True)
@utils.add_CORS_header
@utils.json_view
def crash_verify(request):
    """Verifies crash data in crash data destinations"""
    crash_id = request.GET.get("crash_id", None)

    if not crash_id or not is_crash_id_valid(crash_id):
        return http.JsonResponse({"error": "unknown crash id"}, status=400)

    data = {"uuid": crash_id}

    # Check S3 crash bucket for raw and processed crash data
    raw_api = models.RawCrash()
    try:
        raw_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_raw_crash = True
    except CrashIDNotFound:
        has_raw_crash = False
    data["s3_raw_crash"] = has_raw_crash

    processed_api = models.ProcessedCrash()
    try:
        processed_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_processed_crash = True
    except CrashIDNotFound:
        has_processed_crash = False
    data["s3_processed_crash"] = has_processed_crash

    # Check Elasticsearch for crash data
    supersearch_api = supersearch_models.SuperSearch()
    params = {
        "_columns": ["uuid"],
        "_results_number": 1,
        "uuid": crash_id,
        "dont_cache": True,
        "refresh_cache": True,
    }
    results = supersearch_api.get(**params)
    data["elasticsearch_crash"] = (
        results["total"] == 1 and results["hits"][0]["uuid"] == crash_id
    )

    # Check S3 telemetry bucket for crash data
    telemetry_api = models.TelemetryCrash()
    try:
        telemetry_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_telemetry_crash = True
    except CrashIDNotFound:
        has_telemetry_crash = False
    data["s3_telemetry_crash"] = has_telemetry_crash

    return http.HttpResponse(json.dumps(data), content_type="application/json")
