# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy

from crashstats import productlib
from crashstats.crashstats import models
from crashstats.supersearch.libsupersearch import (
    SUPERSEARCH_FIELDS,
    SuperSearchStatusModel,
)
from socorro.external.es import query
from socorro.external.es import supersearch
from socorro.external.es.super_search_fields import get_source_key
from socorro.lib import BadArgumentError


SUPERSEARCH_META_PARAMS = (
    ("_aggs.product.version", list),
    ("_aggs.android_cpu_abi.android_manufacturer.android_model", list),
    ("_columns", list),
    ("_facets", list),
    ("_facets_size", int),
    "_fields",
    ("_results_offset", int),
    ("_results_number", int),
    "_return_query",
    ("_sort", list),
)


# Those parameters contain list of fields and thus need to be verified before
# sent to the middleware, so that no private field can be accessed.
PARAMETERS_LISTING_FIELDS = (
    "_aggs.product.version",
    "_aggs.android_cpu_abi.android_manufacturer.android_model",
    "_facets",
)


def get_api_allowlist(include_all_fields=False):
    """Returns an API_ALLOWLIST value based on SUPERSEARCH_FIELDS"""

    all_fields = SUPERSEARCH_FIELDS
    fields = []
    for meta in all_fields.values():
        if (
            meta["name"] not in fields
            and meta["is_returned"]
            and (include_all_fields or not meta["permissions_needed"])
        ):
            fields.append(meta["name"])

    return {"hits": fields}


class ESSocorroMiddleware(models.SocorroMiddleware):
    implementation_config_namespace = "elasticsearch"

    post = None
    put = None
    delete = None


def validate_products(product_value):
    """Validates product values against supported products.

    :param product_value: str or list of str denoting products

    :raises BadArgumentError: if there are invalid products specified

    """
    if not product_value:
        return

    if isinstance(product_value, str):
        product_value = [product_value]

    # Do some data validation here before we go further to reduce efforts
    valid_products = {product.name for product in productlib.get_products()}
    invalid_products = set(product_value) - valid_products
    if invalid_products:
        invalid_products_str = ", ".join(invalid_products)
        raise BadArgumentError(f"Not valid products: {invalid_products_str}")


class SuperSearch(ESSocorroMiddleware):
    implementation = supersearch.SuperSearch

    IS_PUBLIC = True

    HELP_TEXT = """
    API for searching and faceting on crash reports.
    """

    API_ALLOWLIST = get_api_allowlist()

    def __init__(self):
        self.all_fields = SUPERSEARCH_FIELDS

        # These fields contain lists of other fields. Later on, we want to
        # make sure that none of those listed fields are restricted.
        self.parameters_listing_fields = list(PARAMETERS_LISTING_FIELDS)

        self.extended_fields = self._get_extended_params()
        for field in self.extended_fields:
            if "_histogram." in field[0] or "_aggs." in field[0]:
                self.parameters_listing_fields.append(field[0])

        self.possible_params = (
            tuple(
                (x["name"], list)
                for x in self.all_fields.values()
                if x["is_exposed"] and not x["permissions_needed"]
            )
            + SUPERSEARCH_META_PARAMS
            + tuple(self.extended_fields)
        )

    def _get_extended_params(self):
        # Add histogram fields for all 'date' or 'number' fields.
        extended_fields = []
        for field in self.all_fields.values():
            if not field["is_exposed"] or field["permissions_needed"]:
                continue

            extended_fields.append(("_aggs.%s" % field["name"], list))

            if field["query_type"] in ("date", "number"):
                extended_fields.append(("_histogram.%s" % field["name"], list))

                # Intervals can be strings for dates (like "day" or "1.5h")
                # and can only be integers for numbers.
                interval_type = {"date": str, "number": int}.get(field["query_type"])

                extended_fields.append(
                    ("_histogram_interval.%s" % field["name"], interval_type)
                )

        return tuple(extended_fields)

    def get(self, **kwargs):
        # Sanitize all parameters listing fields and make sure no private data
        # is requested.

        # Initialize the list of allowed fields with all the fields we know
        # that are returned and do not require any permission.
        allowed_fields = {
            x
            for x in self.all_fields
            if self.all_fields[x]["is_returned"]
            and not self.all_fields[x]["permissions_needed"]
        }

        # Extend that list with the special fields, like `_histogram.*`.
        # Those are accepted values for fields listing other fields.
        for field in self.extended_fields:
            histogram = field[0]
            if not histogram.startswith("_histogram."):
                continue

            field_name = histogram[len("_histogram.") :]
            if (
                field_name in self.all_fields
                and self.all_fields[field_name]["is_returned"]
                and not self.all_fields[field_name]["permissions_needed"]
            ):
                allowed_fields.add(histogram)

        for field in set(allowed_fields):
            allowed_fields.add("_cardinality.%s" % field)

        # Now make sure all fields listing fields only have unrestricted
        # values.
        for param in self.parameters_listing_fields:
            values = kwargs.get(param, [])
            filtered_values = [x for x in values if x in allowed_fields]
            kwargs[param] = filtered_values

        # SuperSearch requires that the list of fields be passed to it.
        kwargs["_fields"] = self.all_fields

        # Do some data validation here before we go further to reduce efforts
        validate_products(kwargs.get("product"))

        return super().get(**kwargs)


class SuperSearchUnredacted(SuperSearch):
    IS_PUBLIC = True

    HELP_TEXT = """
    API for searching and faceting on crash reports. Requires permissions depending on
    which fields are being queried.
    """

    API_ALLOWLIST = get_api_allowlist(include_all_fields=True)

    implementation = supersearch.SuperSearch

    def __init__(self):
        self.all_fields = SUPERSEARCH_FIELDS

        histogram_fields = self._get_extended_params()

        self.possible_params = (
            tuple(
                (x["name"], list) for x in self.all_fields.values() if x["is_exposed"]
            )
            + SUPERSEARCH_META_PARAMS
            + histogram_fields
        )

        permissions = {}
        for field_data in self.all_fields.values():
            for perm in field_data["permissions_needed"]:
                permissions[perm] = True

        self.API_REQUIRED_PERMISSIONS = tuple(permissions.keys())

    def get(self, **kwargs):
        # SuperSearch requires that the list of fields be passed to it.
        kwargs["_fields"] = self.all_fields

        # Do some data validation here before we go further to reduce efforts
        validate_products(kwargs.get("product"))

        # Notice that here we use `SuperSearch` as the class, so that we
        # shortcut the `get` function in that class. The goal is to avoid
        # the _facets field cleaning.
        return super(SuperSearch, self).get(**kwargs)


class SuperSearchFields(ESSocorroMiddleware):
    _fields = SUPERSEARCH_FIELDS

    IS_PUBLIC = True

    HELP_TEXT = """
    API for getting the list of super search fields.
    """

    API_ALLOWLIST = None

    def get(self, **kwargs):
        return copy.deepcopy(self._fields)

    def get_by_source_key(self, key):
        for field in self.get().values():
            if get_source_key(field) == key:
                return field


class SuperSearchStatus(ESSocorroMiddleware):
    implementation = SuperSearchStatusModel

    cache_seconds = 0


class Query(ESSocorroMiddleware):
    # No API_ALLOWLIST because this can't be accessed through the public API.

    implementation = query.Query

    required_params = ("query",)

    possible_params = ("indices",)
