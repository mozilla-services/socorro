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

    # The sort order for this product on the product home page
    home_page_sort: int

    # The list of featured versions on the product page and version drop down; if this
    # has "auto", then it'll automatically generate the list and append any other
    # entries
    featured_versions: List[int]


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


def get_products():
    """Return Product list sorted by home_page_sort value"""
    global _PRODUCTS
    if not _PRODUCTS:
        product_files = get_product_files()

        products = []
        for fn in product_files:
            with open(fn, "r") as fp:
                json_data = json.load(fp)

                # Take out any fields that start with _ so people can add "comments" to
                # the file
                json_data = {
                    key: json_data[key] for key in json_data if not key.startswith("_")
                }

                products.append(Product(**json_data))

        products.sort(key=lambda prod: (prod.home_page_sort, prod.name))
        _PRODUCTS = products

    return _PRODUCTS


class ProductDoesNotExist(Exception):
    pass


def get_product_by_name(name):
    """Returns Product by name"""
    try:
        return [prod for prod in get_products() if prod.name == name][0]
    except IndexError:
        raise ProductDoesNotExist("%s does not exist" % name)


class ProductValidationError(Exception):
    pass


def validate_product_file(fn):
    """Validate a product_file

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
