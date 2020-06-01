# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from django.shortcuts import render

from crashstats.crashstats.decorators import pass_default_context
from crashstats.supersearch.models import SuperSearchFields


OPERATORS_BASE = [""]
OPERATORS_STRING = ["=", "~", "$", "^"]
OPERATORS_RANGE = [">=", "<=", "<", ">"]
OPERATORS_BOOLEAN = ["__true__"]
OPERATORS_FLAG = ["__null__"]
OPERATORS_MAP = {
    "string": OPERATORS_BASE + OPERATORS_STRING + OPERATORS_FLAG,
    "number": OPERATORS_BASE + OPERATORS_RANGE,
    "date": OPERATORS_RANGE,
    "bool": OPERATORS_BOOLEAN,
    "flag": OPERATORS_FLAG,
    "enum": OPERATORS_BASE,
}


@pass_default_context
def home(request, default_context=None):
    context = default_context or {}

    return render(request, "documentation/home.html", context)


@pass_default_context
def protected_data_access(request, default_context=None):
    context = default_context or {}
    return render(request, "documentation/protected_data_access.html", context)


@pass_default_context
def supersearch_home(request, default_context=None):
    context = default_context or {}
    return render(request, "documentation/supersearch/home.html", context)


@pass_default_context
def supersearch_examples(request, default_context=None):
    context = default_context or {}

    context["today"] = datetime.datetime.utcnow().date()
    context["yesterday"] = context["today"] - datetime.timedelta(days=1)
    context["three_days_ago"] = context["today"] - datetime.timedelta(days=3)

    return render(request, "documentation/supersearch/examples.html", context)


@pass_default_context
def supersearch_api(request, default_context=None):
    context = default_context or {}

    all_fields = SuperSearchFields().get().values()
    all_fields = [x for x in all_fields if x["is_returned"]]
    all_fields = sorted(all_fields, key=lambda x: x["name"].lower())

    aggs_fields = list(all_fields)

    # Those fields are hard-coded in `supersearch/models.py`.
    aggs_fields.append({"name": "product.version", "is_exposed": False})
    aggs_fields.append(
        {
            "name": "android_cpu_abi.android_manufacturer.android_model",
            "is_exposed": False,
        }
    )

    date_number_fields = [
        x for x in all_fields if x["query_type"] in ("number", "date")
    ]

    context["all_fields"] = all_fields
    context["aggs_fields"] = aggs_fields
    context["date_number_fields"] = date_number_fields

    context["operators"] = OPERATORS_MAP

    return render(request, "documentation/supersearch/api.html", context)
