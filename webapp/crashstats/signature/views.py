# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import functools
import math

from django import http
from django.conf import settings
from django.shortcuts import render
from django.urls import reverse

from csp.decorators import csp_update
from socorro.lib import BadArgumentError

from crashstats import libproduct
from crashstats.crashstats import models, utils
from crashstats.crashstats.decorators import pass_default_context, track_view
from crashstats.crashstats.utils import SignatureStats, render_exception, urlencode_obj
from crashstats.supersearch.utils import get_date_boundaries

from crashstats.supersearch.models import SuperSearchFields, SuperSearchUnredacted
from crashstats.supersearch.views import ValidationError, get_allowed_fields, get_params


DEFAULT_COLUMNS = (
    "date",
    "product",
    "version",
    "build_id",
    "platform",
    "reason",
    "address",
    "install_time",
    "startup_crash",
)

DEFAULT_SORT = ("-date",)

# These products are supported by correlations. Looking at the signature report
# and filtering on other products will not show the correlations tab.
#
# NOTE(willkg): To add support for another product, you have to add a url
# to crashstats/static/crashstats/js/socorro/correlations.js getDataURL.
CORRELATIONS_PRODUCTS = ["Firefox"]


def pass_validated_params(view):
    @functools.wraps(view)
    def inner(request, *args, **kwargs):
        try:
            params = get_params(request)

            if len(params["signature"]) > 1:
                raise ValidationError(
                    'Invalid value for "signature" parameter, only one value is accepted'
                )

            if not params["signature"] or not params["signature"][0]:
                raise ValidationError('"signature" parameter is mandatory')

            if "\x00" in params["signature"][0]:
                raise ValidationError('"signature" cannot contain nulls')

        except ValidationError as e:
            return http.HttpResponseBadRequest(str(e))

        args += (params,)
        return view(request, *args, **kwargs)

    return inner


def get_fields(user):
    """Retrieve super search fields this user has access to

    :arg user: a Django User instance

    :returns: a list of dicts with "id" and "text" keys

    """
    return sorted(
        x["name"]
        for x in SuperSearchFields().get().values()
        if x["is_exposed"]
        and x["is_returned"]
        and user.has_perms(x["webapp_permissions_needed"])
        and x["name"] != "signature"  # exclude the signature field
    )


@track_view
@csp_update({"connect-src": "analysis-output.telemetry.mozilla.org"})
@pass_validated_params
@pass_default_context
def signature_report(request, params, default_context=None):
    context = default_context

    signature = request.GET.get("signature")
    if not signature:
        return http.HttpResponseBadRequest('"signature" parameter is mandatory')

    context["signature"] = signature

    fields = get_fields(request.user)
    context["fields"] = [
        {"id": field, "text": field.replace("_", " ")} for field in fields
    ]

    columns = request.GET.getlist("_columns")
    columns = [x for x in columns if x in fields]
    context["columns"] = columns or DEFAULT_COLUMNS

    sort = request.GET.getlist("_sort")
    sort = [x for x in sort if x in fields]
    context["sort"] = sort or DEFAULT_SORT

    context["channels"] = ",".join(settings.CHANNELS).split(",")
    context["channel"] = settings.CHANNEL

    context["correlations_products"] = CORRELATIONS_PRODUCTS

    # Compute dates to show them to the user.
    start_date, end_date = get_date_boundaries(params)
    context["query"] = {"start_date": start_date, "end_date": end_date}

    return render(request, "signature/signature_report.html", context)


@track_view
@pass_validated_params
def signature_reports(request, params):
    """Return the results of a search."""

    signature = params["signature"][0]

    context = {}
    context["query"] = {"total": 0, "total_count": 0, "total_pages": 0}

    allowed_fields = get_allowed_fields(request.user)

    current_query = request.GET.copy()
    if "page" in current_query:
        del current_query["page"]

    context["params"] = current_query.copy()

    if "_sort" in context["params"]:
        del context["params"]["_sort"]

    if "_columns" in context["params"]:
        del context["params"]["_columns"]

    context["sort"] = request.GET.getlist("_sort")
    context["columns"] = request.GET.getlist("_columns") or DEFAULT_COLUMNS

    # Make sure only allowed fields are used.
    context["sort"] = [
        x
        for x in context["sort"]
        if x in allowed_fields or (x.startswith("-") and x[1:] in allowed_fields)
    ]
    context["columns"] = [x for x in context["columns"] if x in allowed_fields]

    params["_sort"] = context["sort"]

    # Copy the list of columns so that they can differ.
    params["_columns"] = list(context["columns"])

    # The uuid is always displayed in the UI so we need to make sure it is
    # always returned by the model.
    if "uuid" not in params["_columns"]:
        params["_columns"].append("uuid")

    # We require the cpu_info field to show a special marker on some AMD CPU
    # related crash reports.
    if "cpu_info" not in params["_columns"]:
        params["_columns"].append("cpu_info")

    # The `uuid` field is a special case, it is always displayed in the first
    # column of the table. Hence we do not want to show it again in the
    # auto-generated list of columns, so we its name from the list of
    # columns to display.
    if "uuid" in context["columns"]:
        context["columns"].remove("uuid")

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        return http.HttpResponseBadRequest("Invalid page")

    if current_page <= 0:
        current_page = 1

    results_per_page = 50
    context["current_page"] = current_page
    context["results_offset"] = results_per_page * (current_page - 1)

    params["signature"] = "=" + signature
    params["_results_number"] = results_per_page
    params["_results_offset"] = context["results_offset"]
    params["_facets"] = []  # We don't need no facets.

    context["current_url"] = "%s?%s" % (
        reverse("signature:signature_report"),
        urlencode_obj(current_query),
    )

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    search_results["total_pages"] = int(
        math.ceil(search_results["total"] / float(results_per_page))
    )
    search_results["total_count"] = search_results["total"]

    context["query"] = search_results

    return render(request, "signature/signature_reports.html", context)


@track_view
@pass_validated_params
def signature_aggregation(request, params, aggregation):
    """Return the aggregation of a field."""

    signature = params["signature"][0]

    context = {}
    context["aggregation"] = aggregation

    allowed_fields = get_allowed_fields(request.user)

    # Make sure the field we want to aggregate on is allowed.
    if aggregation not in allowed_fields:
        return http.HttpResponseBadRequest(
            "<ul><li>"
            'You are not allowed to aggregate on the "%s" field'
            "</li></ul>" % aggregation
        )

    current_query = request.GET.copy()
    context["params"] = current_query.copy()

    params["signature"] = "=" + signature
    params["_results_number"] = 0
    params["_results_offset"] = 0
    params["_facets"] = [aggregation]

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    context["aggregates"] = []
    if aggregation in search_results["facets"]:
        context["aggregates"] = search_results["facets"][aggregation]

    context["total_count"] = search_results["total"]

    return render(request, "signature/signature_aggregation.html", context)


@track_view
@utils.json_view
@pass_validated_params
def signature_graphs(request, params, field):
    """Return a multi-line graph of crashes per day grouped by field."""

    signature = params["signature"][0]

    context = {}
    context["aggregation"] = field

    allowed_fields = get_allowed_fields(request.user)

    # Make sure the field we want to aggregate on is allowed.
    if field not in allowed_fields:
        return http.HttpResponseBadRequest(
            '<ul><li>You are not allowed to group by the "%s" field</li></ul>' % field
        )

    current_query = request.GET.copy()
    context["params"] = current_query.copy()

    params["signature"] = "=" + signature
    params["_results_number"] = 0
    params["_results_offset"] = 0
    params["_histogram.date"] = [field]
    params["_facets"] = [field]

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    context["aggregates"] = search_results["facets"].get("histogram_date", [])
    context["term_counts"] = search_results["facets"].get(field, [])

    return context


@track_view
@pass_validated_params
def signature_comments(request, params):
    """Return a list of non-empty comments."""
    # Users can't see comments unless they have view_pii permissions.
    if not request.user.has_perm("crashstats.view_pii"):
        return http.HttpResponseForbidden()

    signature = params["signature"][0]

    context = {}
    context["query"] = {"total": 0, "total_count": 0, "total_pages": 0}

    current_query = request.GET.copy()
    if "page" in current_query:
        del current_query["page"]

    context["params"] = current_query.copy()

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        return http.HttpResponseBadRequest("Invalid page")

    if current_page <= 0:
        current_page = 1

    results_per_page = 50
    context["current_page"] = current_page
    context["results_offset"] = results_per_page * (current_page - 1)

    params["signature"] = "=" + signature
    params["user_comments"] = "!__null__"
    params["_columns"] = ["uuid", "user_comments", "date", "useragent_locale"]
    params["_sort"] = "-date"
    params["_results_number"] = results_per_page
    params["_results_offset"] = context["results_offset"]
    params["_facets"] = []

    context["current_url"] = "%s?%s" % (
        reverse("signature:signature_report"),
        urlencode_obj(current_query),
    )

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    search_results["total_pages"] = int(
        math.ceil(search_results["total"] / float(results_per_page))
    )
    search_results["total_count"] = search_results["total"]

    context["query"] = search_results

    return render(request, "signature/signature_comments.html", context)


@track_view
@pass_validated_params
def signature_correlations(request, params):
    """Guess the best channel and product to use for correlations."""
    context = {}

    context["channel"] = "release"
    if "release_channel" in params and len(params["release_channel"]) == 1:
        context["channel"] = params["release_channel"][0]
    elif "version" in params and params["version"]:
        if all("b" in version for version in params["version"]):
            context["channel"] = "beta"
        elif all("a1" in version for version in params["version"]):
            context["channel"] = "nightly"
        elif all("esr" in version for version in params["version"]):
            context["channel"] = "esr"

    default_product_name = libproduct.get_default_product().name
    product_name = params.get("product") or default_product_name
    if isinstance(product_name, (list, tuple)):
        product_name = product_name[0]

    context["product_name"] = product_name

    return render(request, "signature/signature_correlations.html", context)


@track_view
@pass_validated_params
def signature_summary(request, params):
    """Return a list of specific aggregations"""
    context = {}

    params["signature"] = "=" + params["signature"][0]
    params["_aggs.signature"] = [
        "process_type",
        "startup_crash",
        "dom_fission_enabled",
        "_histogram.uptime",
    ]
    params["_results_number"] = 0
    params["_facets"] = [
        "platform_pretty_version",
        "cpu_arch",
        "process_type",
    ]
    params["_histogram.uptime"] = ["product"]
    params["_histogram_interval.uptime"] = 60
    params["_aggs.adapter_vendor_id"] = ["adapter_device_id"]
    params["_aggs.android_cpu_abi.android_manufacturer.android_model"] = [
        "android_version"
    ]
    params["_aggs.product.version"] = ["_cardinality.install_time"]

    api = SuperSearchUnredacted()

    # Now make the actual request with all expected parameters.
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    facets = search_results["facets"]

    _transform_uptime_summary(facets)
    _transform_graphics_summary(facets)
    _transform_mobile_summary(facets)

    context["query"] = search_results
    context["product_version_total"] = search_results["total"]
    if "signature" in facets and len(facets["signature"]) > 0:
        context["signature_stats"] = SignatureStats(
            search_results["facets"]["signature"][0], search_results["total"]
        )

    return render(request, "signature/signature_summary.html", context)


def _transform_graphics_summary(facets):
    # Augment graphics adapter with data from another service.
    if "adapter_vendor_id" in facets:
        vendor_hexes = []
        adapter_hexes = []
        for vendor in facets["adapter_vendor_id"]:
            for adapter in vendor["facets"]["adapter_device_id"]:
                vendor_hexes.append(vendor["term"])
                adapter_hexes.append(adapter["term"])

        all_names = models.GraphicsDevice.objects.get_pairs(vendor_hexes, adapter_hexes)
        graphics = []
        for vendor in facets["adapter_vendor_id"]:
            for adapter in vendor["facets"]["adapter_device_id"]:
                entry = {
                    "vendor": vendor["term"],
                    "adapter": adapter["term"],
                    "count": adapter["count"],
                }
                key = (vendor["term"], adapter["term"])
                names = all_names.get(key)
                if names and names[0]:
                    entry["vendor"] = "%s (%s)" % (names[0], vendor["term"])
                if names and names[1]:
                    entry["adapter"] = "%s (%s)" % (names[1], adapter["term"])

                graphics.append(entry)

        # By default, results are sorted by vendor count then adapter count.
        # We instead need to sort them by adapter count only. That cannot be
        # done in SuperSearch directly, so we do it here.
        facets["adapter_vendor_id"] = sorted(
            graphics, key=lambda x: x["count"], reverse=True
        )


def _transform_uptime_summary(facets):
    # Transform uptime data to be easier to consume.
    # Keys are in minutes.
    if "histogram_uptime" in facets:
        labels = {
            0: "< 1 min",
            1: "1-5 min",
            5: "5-15 min",
            15: "15-60 min",
            60: "> 1 hour",
        }
        uptimes_count = {x: 0 for x in labels}

        for uptime in facets["histogram_uptime"]:
            for uptime_minutes in sorted(uptimes_count.keys(), reverse=True):
                uptime_seconds = uptime_minutes * 60

                if uptime["term"] >= uptime_seconds:
                    uptimes_count[uptime_minutes] += uptime["count"]
                    break

        uptimes = [
            {"term": labels.get(key), "count": count}
            for key, count in uptimes_count.items()
            if count > 0
        ]
        uptimes = sorted(uptimes, key=lambda x: x["count"], reverse=True)

        facets["histogram_uptime"] = uptimes


def _transform_mobile_summary(facets):
    if "android_cpu_abi" in facets:
        mobile_devices = []

        for cpu_abi in facets["android_cpu_abi"]:
            for manufacturer in cpu_abi["facets"]["android_manufacturer"]:
                for model in manufacturer["facets"]["android_model"]:
                    for version in model["facets"]["android_version"]:
                        mobile_devices.append(
                            {
                                "cpu_abi": cpu_abi["term"],
                                "manufacturer": manufacturer["term"],
                                "model": model["term"],
                                "version": version["term"],
                                "count": version["count"],
                            }
                        )

        facets["android_cpu_abi"] = mobile_devices


@track_view
@pass_validated_params
def signature_bugzilla(request, params):
    """Return a list of associated bugs"""
    context = {}

    signature = params["signature"][0]
    context["signature"] = signature
    context["bugs"] = list(
        models.BugAssociation.objects.get_bugs_and_related_bugs(signatures=[signature])
        .values("bug_id", "signature")
        .order_by("-bug_id")
    )

    return render(request, "signature/signature_bugzilla.html", context)
