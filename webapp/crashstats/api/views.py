# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from functools import wraps
import inspect
import re

from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from rest_framework.exceptions import Throttled
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.utils.urls import replace_query_param
from rest_framework.views import APIView

from django import http
from django import forms
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.sites.requests import RequestSite
from django.core.paginator import Paginator
from django.core.validators import ProhibitNullCharactersValidator
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from crashstats.api.cleaner import Cleaner
from crashstats.crashstats import models
from crashstats.crashstats import utils
from crashstats.crashstats.decorators import track_view, pass_default_context
from crashstats.supersearch import models as supersearch_models
from crashstats.tokens import models as tokens_models
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib import BadArgumentError, MissingArgumentError
from socorro.lib.libooid import is_crash_id_valid
from socorro.signature.generator import SignatureGenerator


# List of all modules that contain models we want to expose.
MODELS_MODULES = (models, supersearch_models)


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
    float: forms.FloatField,
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


def is_valid_model_class(model):
    return isinstance(model, type) and (
        (
            issubclass(model, models.SocorroMiddleware)
            and model is not models.SocorroMiddleware
            and model is not supersearch_models.ESSocorroMiddleware
        )
        or issubclass(model, SocorroAPIView)
    )


def clear_empty_session(fun):
    """Clears empty sessions so they don't persist"""

    @wraps(fun)
    def _clear_empty_session(request, *args, **kwargs):
        # Run the function
        ret = fun(request, *args, **kwargs)

        # Clear the session if nothing was saved to it and it was generated using a
        # token login
        session_keys = [
            key for key in request.session.keys() if not key.startswith("_auth_user")
        ]
        if not session_keys and getattr(request.user, "token_login", False):
            request.session.clear()
            request.session.flush()
        return ret

    return _clear_empty_session


def reject_unknown_models(view):
    @wraps(view)
    def inner(request, model_name, **kwargs):
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

        if model is None or not is_valid_model_class(model) or not model.IS_PUBLIC:
            return http.JsonResponse(
                {"error": f"No service called '{model_name}'"}, status=404
            )

        return view(request, model_name=model_name, model=model, **kwargs)

    return inner


# NOTE(willkg): This rejects unknown models before tracking the view so we're not
# getting metrics on fuzzing attempts on the API.
@reject_unknown_models
@track_view
@csrf_exempt
@clear_empty_session
@ratelimit(
    key="ip", method=["GET", "POST", "PUT"], rate=utils.ratelimit_rate, block=True
)
@utils.json_view
def model_wrapper(request, model_name, model):
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

    function = None
    if request.method == "POST":
        function = instance.post
    elif request.method == "GET":
        function = instance.get
    elif request.method == "OPTIONS":
        function = instance.options

    if function is None:
        return http.JsonResponse({"error": "Method not allowed"}, status=405)

    # assume first that it won't need a binary response
    binary_response = False

    if request.method == "OPTIONS":
        # NOTE(willkg): OPTIONS requests are for CORS preflights. Because of the way
        # this API infra is written, we don't know whether the API endpoint is a GET or
        # POST (or both?) so we don't know where the required params are coming from, so
        # we ignore checking them here.
        try:
            result = function()
        except NOT_FOUND_EXCEPTIONS:
            return http.JsonResponse({"error": "Not found"}, status=404)
        except BAD_REQUEST_EXCEPTIONS as exception:
            return http.JsonResponse(
                {"error": f"Bad request: {type(exception).__name__} {exception}"},
                status=400,
            )

    elif request.method in ["GET", "POST"]:
        request_data = request.method == "GET" and request.GET or request.POST
        form = MiddlewareModelForm(model, request_data)
        if form.is_valid():
            try:
                result = function(**form.cleaned_data)
            except NOT_FOUND_EXCEPTIONS as exception:
                return http.JsonResponse(
                    {"error": f"Not found: {type(exception).__name__} {exception}"},
                    status=404,
                )
            except BAD_REQUEST_EXCEPTIONS as exception:
                return http.JsonResponse(
                    {"error": f"Bad request: {type(exception).__name__}: {exception}"},
                    status=400,
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
                    permissions = ", ".join(permission_names)
                    return http.JsonResponse(
                        {
                            "error": f"Binary response requires permissions: {permissions}"
                        },
                        status=403,
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
            return http.JsonResponse({"errors": dict(form.errors)}, status=400)

    if binary_response:
        filename = model.get_binary_filename(form.cleaned_data)
        assert filename is not None, "No API_BINARY_FILENAME set on model"
        response = http.HttpResponse(result, content_type="application/octet-stream")
        response["Content-Disposition"] = 'attachment; filename="%s"' % filename
        return response

    if getattr(model, "deprecation_warning", False):
        if isinstance(result, dict):
            result["DEPRECATION_WARNING"] = model.deprecation_warning
        headers["DEPRECATION-WARNING"] = model.deprecation_warning.replace("\n", " ")

    if model.cache_seconds > 0:
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

    # Also document DRF classes which subclass SocorroAPIView
    for model in SocorroAPIView.__subclasses__():
        all_models.append(model)

    models_with_names = []
    for model in all_models:
        model_name = getattr(model, "API_NAME", model.__name__)
        if model_name.endswith("Middleware"):
            model_name = model_name[:-10]

        if not is_valid_model_class(model) or not model.IS_PUBLIC:
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

    # NOTE(willkg): Models can define get = None or not have the method at all
    if getattr(model, "get", None):
        methods.append("GET")
    elif getattr(model, "post", None):
        methods.append("POST")

    help_text = model.HELP_TEXT or "No description available."
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
        "test_drive": getattr(model, "TEST_DRIVE", True),
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


def handle_ratelimit(fun):
    """Fixes django-ratelimit exception so it ends up as a 429

    Note: This must be before ratelimit so it can handle exceptions.

    """

    @wraps(fun)
    def _handle_ratelimit(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except Ratelimited as exc:
            # If the view is rate limited, we throw a 429.
            raise Throttled() from exc

    return _handle_ratelimit


@csrf_exempt
@handle_ratelimit
@ratelimit(key="ip", method=["GET"], rate=utils.ratelimit_rate, block=True)
@utils.json_view
def crash_verify(request):
    """Verifies crash data in crash data destinations"""
    if request.method == "OPTIONS":
        return http.JsonResponse({}, status=200)

    crash_id = request.GET.get("crash_id", None)

    if not crash_id or not is_crash_id_valid(crash_id):
        return http.JsonResponse({"error": "unknown crash id"}, status=400)

    data = {"uuid": crash_id}

    # Check crash bucket for raw and processed crash data
    raw_api = models.RawCrash()
    try:
        raw_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_raw_crash = True
    except CrashIDNotFound:
        has_raw_crash = False
    data["raw_crash"] = has_raw_crash

    processed_api = models.ProcessedCrash()
    try:
        processed_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_processed_crash = True
    except CrashIDNotFound:
        has_processed_crash = False
    data["processed_crash"] = has_processed_crash

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

    # Check telemetry bucket for crash data
    telemetry_api = models.TelemetryCrash()
    try:
        telemetry_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
        has_telemetry_crash = True
    except CrashIDNotFound:
        has_telemetry_crash = False
    data["telemetry_crash"] = has_telemetry_crash

    return http.JsonResponse(data, status=200)


class SocorroAPIView(APIView):
    """Django REST Framework APIView that supports CORS"""

    cors_headers = {"Access-Control-Allow-Origin": "*"}
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser]

    # Name of the API
    API_NAME = "Unknown"

    # Whether this API is public and documented or a private API we don't tell anyone
    # about
    IS_PUBLIC = False

    # Help text which shows up in the documentation
    HELP_TEXT = ""

    # Whether or not this class supports the "Run Test Drive!" feature of the API docs;
    # POST-based APIs with complex payloads don't work so well
    TEST_DRIVE = False

    # Parity with SocorroMiddleware
    API_REQUIRED_PERMISSIONS = []
    API_BINARY_PERMISSIONS = None
    API_ALLOWLIST = []

    def get_annotated_params(self):
        """This is for parity with SocorroMiddleware."""
        return []

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        # Add cors headers
        for key, val in self.cors_headers.items():
            response[key] = val
        return response


class MissingProcessedCrashAPI(SocorroAPIView):
    """
    API for retrieving list of missing processed crash reports.
    """

    API_NAME = "MissingProcessedCrash"

    IS_PUBLIC = True

    PAGE_SIZE = 1_000

    HELP_TEXT = """
    Retrieves list of missing processed crash report records. Each record denotes a
    crash report that the system thought was missing. Some have been processed since
    then.

    :Method: HTTP GET
    :Argument: (optional) ``page``: 1-based page to retrieve

    Returns

        {"results": [ RECORD+ ]}, "count": COUNT, "next": LINK, "previous": LINK}

    where COUNT is the total number of records in the table, LINK is either null
    or the url to a page, and RECORD is a structure like:

        {"crash_id": CRASHID, "is_processed": BOOL, "created": TIMESTAMP}

    """

    @method_decorator(csrf_exempt)
    @method_decorator(
        ratelimit(key="ip", method=["GET"], rate=utils.ratelimit_rate, block=True)
    )
    def get(self, request):
        qs = models.MissingProcessedCrash.objects.order_by("id").all()
        paginator = Paginator(qs, self.PAGE_SIZE)

        try:
            page_number = int(request.GET.get("page", "1"))
        except ValueError:
            return http.JsonResponse(
                {"error": "invalid page number"}, status=status.HTTP_400_BAD_REQUEST
            )

        page_obj = paginator.get_page(page_number)

        if page_obj.has_next():
            next_link = replace_query_param(
                request.build_absolute_uri(),
                "page",
                page_number + 1,
            )
        else:
            next_link = None

        if page_obj.has_previous():
            previous_link = replace_query_param(
                request.build_absolute_uri(),
                "page",
                page_number - 1,
            )
        else:
            previous_link = None

        # NOTE(willkg): this matches the structure that DRF returns for pagination
        results = {
            "results": [
                {
                    "crash_id": item.crash_id,
                    "is_processed": item.is_processed,
                    "created": item.created,
                }
                for item in page_obj
            ],
            "count": paginator.count,
            "next": next_link,
            "previous": previous_link,
        }
        return Response(results)


class CrashVerifyAPI(SocorroAPIView):
    """
    API to verify crash data exists in data storage locations.
    """

    API_NAME = "CrashVerify"

    @method_decorator(csrf_exempt)
    @method_decorator(
        ratelimit(key="ip", method=["GET"], rate=utils.ratelimit_rate, block=True)
    )
    def get(self, request):
        crash_id = request.GET.get("crash_id", None)

        if not crash_id or not is_crash_id_valid(crash_id):
            return http.JsonResponse(
                {"error": "unknown crash id"}, status=status.HTTP_400_BAD_REQUEST
            )

        data = {"uuid": crash_id}

        # Check crash bucket for raw and processed crash data
        raw_api = models.RawCrash()
        try:
            raw_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
            has_raw_crash = True
        except CrashIDNotFound:
            has_raw_crash = False
        data["raw_crash"] = has_raw_crash

        processed_api = models.ProcessedCrash()
        try:
            processed_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
            has_processed_crash = True
        except CrashIDNotFound:
            has_processed_crash = False
        data["processed_crash"] = has_processed_crash

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

        # Check telemetry bucket for crash data
        telemetry_api = models.TelemetryCrash()
        try:
            telemetry_api.get(crash_id=crash_id, dont_cache=True, refresh_cache=True)
            has_telemetry_crash = True
        except CrashIDNotFound:
            has_telemetry_crash = False
        data["telemetry_crash"] = has_telemetry_crash

        return Response(data)


class CrashSignatureAPI(SocorroAPIView):
    API_NAME = "CrashSignature"

    IS_PUBLIC = True

    HELP_TEXT = """
    Note: This is currently unsupported and in flux. It's being stabilitized. See:
    https://bugzilla.mozilla.org/show_bug.cgi?id=828452

    Takes memory address, module information, and crash annotation data and generates a
    crash signature.

    :Method: HTTP POST
    :Content-Type: application/json

    Payload consists of one or more signature generation jobs. e.g.

        {"jobs": [ JOB+ ]}

    where JOB is the same as the siggen Crash data schema defined here:

    https://github.com/willkg/socorro-siggen/

    This returns results--one for each job. e.g.

        {"results": [ RESULT+ ]}

    where RESULT has "signature", "notes", and "extra" keys.
    """

    @method_decorator(csrf_exempt)
    @method_decorator(handle_ratelimit)
    @method_decorator(
        ratelimit(key="ip", method=["POST"], rate=utils.ratelimit_rate, block=True)
    )
    def post(self, request):
        is_debug = request.META.get("DEBUG", "0") == "1"
        # FIXME(willkg): add payload schema validation if is_debug is true

        signature_generator = SignatureGenerator()

        jobs = request.data.get("jobs", [])
        if not jobs:
            return http.JsonResponse(
                {"error": "no jobs specified"}, status=status.HTTP_400_BAD_REQUEST
            )

        results = []
        for job in jobs:
            result = signature_generator.generate(job)
            result = result.to_dict()
            # If it's _not_ a debug request, then remove the debug log
            if not is_debug:
                del result["debug_log"]
            results.append(result)

        return Response({"results": results})
