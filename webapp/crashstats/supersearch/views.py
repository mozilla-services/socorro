# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict
import datetime
import json
import math

from django import http
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from django_ratelimit.decorators import ratelimit

from crashstats import libproduct
from crashstats.crashstats import models, utils
from crashstats.crashstats.decorators import track_view
from crashstats.crashstats.utils import render_exception, urlencode_obj
from crashstats.crashstats.views import pass_default_context
from crashstats.supersearch import forms
from crashstats.supersearch.models import (
    Query,
    SuperSearchFields,
    SuperSearchUnredacted,
)
from socorro import settings as socorro_settings
from socorro.lib import BadArgumentError
from socorro.libclass import build_instance_from_settings


DEFAULT_COLUMNS = ("date", "signature", "product", "version", "build_id", "platform")

DEFAULT_FACETS = ("signature",)

DEFAULT_SORT = ("-date",)

# Facetting on those fields doesn't provide useful information.
EXCLUDED_FIELDS_FROM_FACETS = ("date",)


DEFAULT_DATE_RANGE_DAYS = 7


class ValidationError(Exception):
    pass


def get_allowed_fields(user):
    return tuple(
        x["name"]
        for x in SuperSearchFields().get().values()
        if x["is_exposed"] and user.has_perms(x["webapp_permissions_needed"])
    )


def get_supersearch_form(request):
    platforms = list(models.Platform.objects.values_list("name", flat=True))
    products = [product.name for product in libproduct.get_products()]

    # FIXME(willkg): this hardcodes always getting Firefox versions which
    # seems unhelpful
    product_versions = utils.get_versions_for_product("Firefox")

    all_fields = SuperSearchFields().get()

    form = forms.SearchForm(
        all_fields, products, product_versions, platforms, request.user, request.GET
    )
    return form


def get_params(request):
    form = get_supersearch_form(request)

    if not form.is_valid():
        raise ValidationError(str(form.errors))

    params = {}
    for key in form.cleaned_data:
        if hasattr(form.fields[key], "prefixed_value"):
            value = form.fields[key].prefixed_value
        else:
            value = form.cleaned_data[key]

        params[key] = value

    params["_sort"] = request.GET.getlist("_sort")
    params["_facets"] = request.GET.getlist("_facets", DEFAULT_FACETS)
    params["_columns"] = request.GET.getlist("_columns") or DEFAULT_COLUMNS

    allowed_fields = get_allowed_fields(request.user)

    # Make sure only allowed fields are used.
    params["_sort"] = [
        x
        for x in params["_sort"]
        if x in allowed_fields or (x.startswith("-") and x[1:] in allowed_fields)
    ]
    params["_facets"] = [x for x in params["_facets"] if x in allowed_fields]
    params["_columns"] = [x for x in params["_columns"] if x in allowed_fields]

    # The uuid is always displayed in the UI so we need to make sure it is
    # always returned by the model.
    if "uuid" not in params["_columns"]:
        params["_columns"].append("uuid")

    return params


@track_view
@pass_default_context
def search(request, default_context=None):
    allowed_fields = get_allowed_fields(request.user)

    context = default_context
    context["possible_facets"] = [
        {"id": x, "text": x.replace("_", " ")}
        for x in allowed_fields
        if x not in EXCLUDED_FIELDS_FROM_FACETS
    ]

    context["possible_columns"] = [
        {"id": x, "text": x.replace("_", " ")} for x in allowed_fields
    ]

    context["sort"] = request.GET.getlist("_sort", DEFAULT_SORT)
    context["facets"] = request.GET.getlist("_facets", DEFAULT_FACETS)
    context["columns"] = request.GET.getlist("_columns") or DEFAULT_COLUMNS

    # Fields data for the simple search UI.
    form = get_supersearch_form(request)
    context["simple_search_data"] = [
        # field name, options, placeholder values
        (
            x,
            [c[1] for c in form.fields[x].choices],
            [c[1] for c in form.fields[x].choices[:3]],
        )
        for x in settings.SIMPLE_SEARCH_FIELDS
    ]
    context["simple_search_data_fields"] = list(settings.SIMPLE_SEARCH_FIELDS)

    # Default dates for the date filters.
    now = timezone.now()
    context["dates"] = {
        "to": now,
        "from": now - datetime.timedelta(days=DEFAULT_DATE_RANGE_DAYS),
    }

    return render(request, "supersearch/search.html", context)


@track_view
@ratelimit(key="ip", rate=utils.ratelimit_rate, method=ratelimit.ALL, block=True)
def search_results(request):
    """Return the results of a search"""
    try:
        params = get_params(request)
    except ValidationError as e:
        # There was an error in the form, let's return it.
        return http.HttpResponseBadRequest(str(e))

    context = {}
    context["query"] = {"total": 0, "total_count": 0, "total_pages": 0}

    current_query = request.GET.copy()
    if "page" in current_query:
        del current_query["page"]

    context["params"] = current_query.copy()

    if "_columns" in context["params"]:
        del context["params"]["_columns"]

    if "_facets" in context["params"]:
        del context["params"]["_facets"]

    context["sort"] = list(params["_sort"])

    # Copy the list of columns so that they can differ.
    context["columns"] = list(params["_columns"])

    # The `uuid` field is a special case, it is always displayed in the first
    # column of the table. Hence we do not want to show it again in the
    # auto-generated list of columns, so we remove it from the list of
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

    params["_results_number"] = results_per_page
    params["_results_offset"] = context["results_offset"]

    context["current_url"] = "%s?%s" % (
        reverse("supersearch:search"),
        urlencode_obj(current_query),
    )

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as exception:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(exception))

    if "signature" in search_results["facets"]:
        # Bugs for each signature
        signatures = [h["term"] for h in search_results["facets"]["signature"]]

        if signatures:
            bugs = defaultdict(list)
            qs = models.BugAssociation.objects.filter(signature__in=signatures).values(
                "bug_id", "signature"
            )
            for item in qs:
                bugs[item["signature"]].append(item["bug_id"])

            for hit in search_results["facets"]["signature"]:
                sig = hit["term"]
                if sig in bugs:
                    if "bugs" in hit:
                        hit["bugs"].extend(bugs[sig])
                    else:
                        hit["bugs"] = bugs[sig]
                    # most recent bugs first
                    hit["bugs"].sort(reverse=True)

    context["simple_search_data_fields"] = list(settings.SIMPLE_SEARCH_FIELDS)

    search_results["total_pages"] = int(
        math.ceil(search_results["total"] / float(results_per_page))
    )
    search_results["total_count"] = search_results["total"]

    context["query"] = search_results

    return render(request, "supersearch/search_results.html", context)


@track_view
@utils.json_view
def search_fields(request):
    """Return JSON document describing fields used by JavaScript dynamic_form library"""
    form = get_supersearch_form(request)
    exclude = request.GET.getlist("exclude")
    return form.get_fields_list(exclude=exclude)


@track_view
@permission_required("crashstats.run_custom_queries")
@pass_default_context
def search_custom(request, default_context=None):
    """Return the basic search page, without any result"""
    error = None
    query = None

    try:
        params = get_params(request)
    except ValidationError as e:
        # There was an error in the form, but we want to do the default
        # behavior and just display an error message.
        error = str(e)
    else:
        # Get the JSON query that supersearch generates and show it.
        params["_return_query"] = "true"
        api = SuperSearchUnredacted()
        try:
            query = api.get(**params)
        except BadArgumentError as e:
            error = e

    es_crashstorage = build_instance_from_settings(socorro_settings.ES_STORAGE)

    possible_indices = []
    for index in es_crashstorage.get_indices():
        possible_indices.append({"id": index, "text": index})

    context = default_context
    context["elasticsearch_indices"] = possible_indices

    if query:
        context["query"] = json.dumps(query["query"])
        context["indices"] = ",".join(sorted(query["indices"]))

    context["error"] = error

    return render(request, "supersearch/search_custom.html", context)


@track_view
@permission_required("crashstats.run_custom_queries")
@require_POST
@utils.json_view
def search_query(request):
    form = forms.QueryForm(request.POST)
    if not form.is_valid():
        return http.HttpResponseBadRequest(form.errors)

    api = Query()
    results = api.get(
        query=form.cleaned_data["query"], indices=form.cleaned_data["indices"]
    )

    return results
