# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Classes and functions for product settings.
"""

from dataclasses import dataclass
import json
import pathlib
from typing import List

from django.conf import settings

from enforce_typing import enforce_types


@enforce_types
@dataclass
class Product:
    # Product name displayed on site
    name: str

    # One-line description of the product
    description: str

    # The sort order for this product on the product home page
    home_page_sort: int

    # The list of featured versions on the product page and version drop down; if this
    # has "auto", then it'll automatically generate the list and append any other
    # entries
    featured_versions: List[int]

    # Whether or not this product has data in Buildhub
    in_buildhub: bool

    # The list of [link name, link url] bug links for creating new bugs from the report
    # view of a crash report
    bug_links: List[List[str]]


# In-memory cache of products files so we're not parsing them over-and-over
_PRODUCTS = []


def delete_cache():
    """Delete the product cache"""
    global _PRODUCTS
    _PRODUCTS = []


def get_product_files():
    """Returns list of file names for product files in product_details directory"""
    product_details_dir = pathlib.Path(settings.SOCORRO_ROOT) / "product_details"
    product_files = list(product_details_dir.glob("*.json"))
    return product_files


def load_product_from_file(fn):
    with open(fn, "r") as fp:
        json_data = json.load(fp)

        # Take out any fields that start with _ so people can add "comments" to
        # the file
        json_data = {
            key: json_data[key] for key in json_data if not key.startswith("_")
        }

        return Product(**json_data)


def get_products():
    """Return Product list sorted by home_page_sort value"""
    global _PRODUCTS
    if not _PRODUCTS:
        product_files = get_product_files()
        products = [load_product_from_file(fn) for fn in product_files]
        products.sort(key=lambda prod: (prod.home_page_sort, prod.name))
        _PRODUCTS = products

    return _PRODUCTS


class ProductDoesNotExist(Exception):
    pass


def get_product_by_name(name):
    """Returns Product by name

    :param str name: the name of the product to get

    :returns: Product

    :raises ProductDoesNotExist: if there are no products

    """
    try:
        return [prod for prod in get_products() if prod.name == name][0]
    except IndexError:
        raise ProductDoesNotExist("%s does not exist" % name)


def get_default_product():
    """Returns the default product

    The default product is the first one in the sort list.

    :returns: Product

    :raises ProductDoesNotExist: if there are no products

    """
    try:
        return get_products()[0]
    except IndexError:
        raise ProductDoesNotExist("there are no products")


class ProductValidationError(Exception):
    pass


def validate_product_file(fn):
    """Validate a product_file

    This is used in the tests for a first-pass automated check that changes to product
    files are correct. This doesn't eliminate the need to verify those changes.

    :param fn: the file name of the product file to verify

    :raise ProductValidationError: if there are problems with the product files;
        note that this fails on the first error

    """
    try:
        with open(fn, "r") as fp:
            json_data = json.load(fp)

            # Remove comments
            json_data = {
                key: json_data[key] for key in json_data if not key.startswith("_")
            }

            # Type validation doesn't verify the shape of bug_links, so we need to do
            # that manually
            for item in json_data["bug_links"]:
                if len(item) != 2:
                    raise ProductValidationError(
                        "product file %s has invalid bug_links: %s" % (fn, repr(item))
                    )
                if not isinstance(item[0], str) or not isinstance(item[1], str):
                    raise ProductValidationError(
                        "product file %s has invalid bug_links: %s" % (fn, repr(item))
                    )

                # NOTE(willkg): This doesn't verify templates are well formed. That's
                # handled in a test in the code that uses the template.

            # Try to build a Product out of it
            Product(**json_data)

    except json.decoder.JSONDecodeError as jde:
        raise ProductValidationError(
            "product file %s can not be decoded: %s" % (fn, jde)
        )

    except PermissionError as exc:
        raise ProductValidationError("product file %s cannot be opened: %s" % (fn, exc))

    except TypeError as exc:
        raise ProductValidationError(
            "product file %s has invalid fields/values: %s" % (fn, exc)
        )
