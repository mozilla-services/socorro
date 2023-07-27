# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import functools
import hashlib
from pathlib import Path

import docutils.core

from django import http
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render

from crashstats import libproduct
from crashstats.crashstats.decorators import pass_default_context, track_view
from crashstats.supersearch.models import SuperSearch, SuperSearchFields
from socorro.lib.libdockerflow import get_version_info, get_release_name
from socorro.lib.libmarkdown import get_markdown
from socorro.lib.libsocorrodataschema import get_schema


OPERATORS_BASE = [""]
OPERATORS_STRING = ["=", "~", "$", "^"]
OPERATORS_RANGE = [">=", "<=", "<", ">"]
OPERATORS_BOOLEAN = ["__true__"]
OPERATORS_FLAG = ["__null__"]
OPERATORS_MAP = {
    "string": OPERATORS_BASE + OPERATORS_STRING + OPERATORS_FLAG,
    "float": OPERATORS_BASE + OPERATORS_RANGE,
    "integer": OPERATORS_BASE + OPERATORS_RANGE,
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


@functools.cache
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
    version_info = get_version_info(settings.SOCORRO_ROOT)
    release = get_release_name(settings.SOCORRO_ROOT)
    version = version_info.get("version", "")
    commit = version_info.get("commit", "")
    if version:
        # This will show in prod
        release_url = (
            f"https://github.com/mozilla-services/socorro/releases/tag/{version}"
        )
    elif commit:
        # This will show on stage
        release_url = f"https://github.com/mozilla-services/socorro/commit/{commit}"
    else:
        release_url = ""

    context = default_context or {}
    context["whatsnew"] = read_whatsnew()
    context["release"] = release
    context["release_url"] = release_url

    return render(request, "docs/whatsnew.html", context)


@track_view
@pass_default_context
def protected_data_access(request, default_context=None):
    context = default_context or {}
    return render(request, "docs/protected_data_access.html", context)


@functools.cache
def get_annotation_schema_data():
    annotation_schema = get_schema("raw_crash.schema.yaml")

    annotation_fields = {
        key: schema_item for key, schema_item in annotation_schema["properties"].items()
    }
    return annotation_fields


@functools.cache
def get_processed_schema_data():
    processed_schema = get_schema("processed_crash.schema.yaml")

    processed_fields = {
        key: schema_item for key, schema_item in processed_schema["properties"].items()
    }
    return processed_fields


@track_view
@pass_default_context
def datadictionary_index(request, default_context=None):
    context = default_context or {}

    context["annotation_fields"] = get_annotation_schema_data()
    context["processed_fields"] = get_processed_schema_data()

    return render(request, "docs/datadictionary/index.html", context)


@functools.cache
def get_processed_field_for_annotation(field):
    field_data = get_processed_schema_data()
    for key, value in field_data.items():
        if value.get("source_annotation") == field:
            return key
    return ""


def get_products_for_annotation(field):
    resp = SuperSearch().get(
        crash_report_keys=f"~{field}",
        _results_number=0,
        _facets=["product"],
        _facets_size=5,
    )
    if "product" in resp["facets"]:
        return [item["term"] for item in resp["facets"]["product"]]


def get_indexed_example_data(field):
    resp = SuperSearch().get(
        _results_number=0,
        _facets=[field],
        _facets_size=5,
    )
    if field in resp["facets"]:
        return [item["term"] for item in resp["facets"][field]]


class DatasetNotFound(Exception):
    pass


class FieldNotFound(Exception):
    pass


DATASET_TO_SCHEMA = {
    "annotation": get_schema("raw_crash.schema.yaml"),
    "processed": get_schema("processed_crash.schema.yaml"),
}


def generate_field_doc(dataset, field):
    try:
        schema = DATASET_TO_SCHEMA[dataset]
    except KeyError as exc:
        raise DatasetNotFound() from exc

    field_hash = hashlib.md5(field.encode("utf-8")).hexdigest()
    cache_key = f"datadictionary:generate_field_doc:{dataset}:{field_hash}"

    ret = cache.get(cache_key)
    if ret is not None:
        return ret

    field_path = field.split("/")
    field_name = field_path[-1]

    # Find the field item they want to view documentation for
    field_data = schema
    for path_item in field_path:
        if path_item == "[]":
            field_data = field_data.get("items")
            if field_data is None:
                raise FieldNotFound()

            continue

        elif path_item in field_data.get("properties", {}):
            field_data = field_data["properties"][path_item]
            continue

        elif field_data.get("pattern_properties", {}):
            nicknamed_fields = {
                field_data_field["nickname"]: field_data_field
                for field_data_field in field_data["pattern_properties"].values()
            }
            field_data = nicknamed_fields.get(path_item)
            if field_data is None:
                raise FieldNotFound()
            continue

        raise FieldNotFound()

    if field_data is None:
        raise FieldNotFound()

    # Get description and examples and render it as markdown
    description = field_data.get("description") or "no description"
    examples = field_data.get("examples") or []
    if examples:
        description = description + "\n- `" + "`\n- `".join(examples) + "`"

    description = get_markdown().render(description)

    # For processed crash fields, add super search information
    search_field = ""
    search_field_query_type = ""
    example_data = []
    if dataset == "processed":
        super_search_field = SuperSearchFields().get_by_source_key(
            f"processed_crash.{field}"
        )
        if super_search_field:
            search_field = super_search_field["name"]
            search_field_query_type = super_search_field["query_type"]
            # FIXME(willkg): we're only doing this for public fields, but we could do
            # this for whatever fields the user can see
            if field_data["permissions"] == ["public"]:
                example_data = get_indexed_example_data(field)

    # For annotations, add the list of products that have emitted this annotation
    # recently
    products = []
    processed_field = ""
    if dataset == "annotation":
        products = get_products_for_annotation(field_name)
        processed_field = get_processed_field_for_annotation(field_name)

    # Determine the breadcrumbs links for parents of this field
    field_path_breadcrumbs = [
        ("/".join(field_path[0 : i + 1]), field_path[i]) for i in range(len(field_path))
    ]

    doc_data = {
        "dataset": dataset,
        "field_name": field_name,
        "field_path_breadcrumbs": field_path_breadcrumbs,
        "field_path": field,
        "field_data": field_data,
        "description": description,
        "data_reviews": field_data.get("data_reviews") or [],
        "example_data": example_data,
        "products_for_field": products,
        "search_field": search_field,
        "search_field_query_type": search_field_query_type,
        "source_annotation": field_data.get("source_annotation") or "",
        "processed_field": processed_field,
        "type": field_data["type"],
        "permissions": field_data["permissions"],
    }

    cache.set(cache_key, doc_data, timeout=60)

    return doc_data


@track_view
@pass_default_context
def datadictionary_field_doc(request, dataset, field, default_context=None):
    try:
        doc_data = generate_field_doc(dataset, field)
    except DatasetNotFound:
        return http.HttpResponseNotFound("Dataset not found")
    except FieldNotFound:
        return http.HttpResponseNotFound("Field not found")

    context = default_context or {}

    context.update(doc_data)
    return render(request, "docs/datadictionary/field_doc.html", context)


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

    product_name = libproduct.get_default_product().name
    context["product_name"] = product_name
    context["version"] = get_valid_version(context["active_versions"], product_name)

    return render(request, "docs/supersearch/home.html", context)


@track_view
@pass_default_context
def supersearch_examples(request, default_context=None):
    context = default_context or {}

    product_name = libproduct.get_default_product().name
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
        x for x in all_fields if x["query_type"] in ("integer", "float", "date")
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
