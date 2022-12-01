# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from functools import cache
from pathlib import Path

import docutils.core

from django.conf import settings
from django.shortcuts import render

from crashstats import productlib
from crashstats.crashstats.decorators import pass_default_context, track_view
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


@track_view
@pass_default_context
def home(request, default_context=None):
    context = default_context or {}

    return render(request, "docs/home.html", context)


@cache
def read_whatsnew():
    """Reads the WHATSNEW.rst file, parses it, and returns the HTML

    :returns: HTML document as string

    """
    path = Path(settings.SOCORRO_ROOT) / "WHATSNEW.rst"

    with open(path, "r") as fp:
        data = fp.read()
        parts = docutils.core.publish_parts(data, writer_name="html")

    return parts["html_body"]


@track_view
@pass_default_context
def whatsnew(request, default_context=None):
    context = default_context or {}
    context["whatsnew"] = read_whatsnew()
    return render(request, "docs/whatsnew.html", context)


@track_view
@pass_default_context
def protected_data_access(request, default_context=None):
    context = default_context or {}
    return render(request, "docs/protected_data_access.html", context)


def get_valid_version(active_versions, product_name):
    """Return version data.

    If this is a local dev environment, then there's no version data.  However, the data
    structures involved are complex and there are a myriad of variations.

    This returns a valid version.

    :arg active_versions: map of product_name -> list of version dicts
    :arg product_name: a product name

    :returns: version as a string

    """
    default_version = {"product": product_name, "version": "80.0"}
    active_versions = active_versions.get("active_versions", {})
    versions = active_versions.get(product_name, []) or [default_version]
    return versions[0]["version"]


@track_view
@pass_default_context
def supersearch_home(request, default_context=None):
    context = default_context or {}

    product_name = productlib.get_default_product().name
    context["product_name"] = product_name
    context["version"] = get_valid_version(context["active_versions"], product_name)

    return render(request, "docs/supersearch/home.html", context)


@track_view
@pass_default_context
def supersearch_examples(request, default_context=None):
    context = default_context or {}

    product_name = productlib.get_default_product().name
    context["product_name"] = product_name
    context["version"] = get_valid_version(context["active_versions"], product_name)
    context["today"] = datetime.datetime.utcnow().date()
    context["yesterday"] = context["today"] - datetime.timedelta(days=1)
    context["three_days_ago"] = context["today"] - datetime.timedelta(days=3)

    return render(request, "docs/supersearch/examples.html", context)


@track_view
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

    return render(request, "docs/supersearch/api.html", context)


@track_view
@pass_default_context
def signup(request, default_context=None):
    context = default_context or {}
    return render(request, "docs/signup.html", context)
