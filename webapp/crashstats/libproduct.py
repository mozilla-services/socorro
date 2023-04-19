# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Classes and functions for product settings.
"""

from dataclasses import dataclass, field
import json
import pathlib
from typing import Dict, List

from enforce_typing import enforce_types
import requests

from django.conf import settings

from socorro.lib.librequests import session_with_retries


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
    featured_versions: List[int] = field(default_factory=list)

    # Map of key to url pointing to JSON file
    version_json_urls: Dict[str, str] = field(default_factory=dict)

    # Whether or not this product has data in Buildhub
    in_buildhub: bool = field(default=False)

    # The list of [link name, link url] bug links for creating new bugs from the report
    # view of a crash report
    bug_links: List[List[str]] = field(default_factory=list)

    # List of [link name, link url] links to display on the product home page
    product_home_links: List[List[str]] = field(default_factory=list)


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
    with open(fn) as fp:
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
    except IndexError as exc:
        raise ProductDoesNotExist(f"{name} does not exist") from exc


class VersionDataError(Exception):
    """Denotes an error with retrieving version data"""


def get_version_json_data(url):
    """Retrieves JSON encoded data at specified url.

    :arg url: the url to fetch

    :returns: data as a dict

    :raises VersionDataError: for errors

    """
    session = session_with_retries()
    resp = session.get(url)
    if resp.status_code == 200:
        try:
            return resp.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise VersionDataError(f"url {url} has invalid JSON") from exc

    raise VersionDataError(f"url {url} returned {resp.status_code}")


def get_default_product():
    """Returns the default product

    The default product is the first one in the sort list.

    :returns: Product

    :raises ProductDoesNotExist: if there are no products

    """
    try:
        return get_products()[0]
    except IndexError as exc:
        raise ProductDoesNotExist("there are no products") from exc


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
        with open(fn) as fp:
            json_data = json.load(fp)

            # Remove comments
            json_data = {
                key: json_data[key] for key in json_data if not key.startswith("_")
            }

            # Type validation doesn't verify the shape of bug_links, so we need to do
            # that manually
            for item in json_data.get("bug_links", []):
                if len(item) != 2:
                    raise ProductValidationError(
                        f"product file {fn} has invalid bug_links: {item!r}"
                    )
                if not isinstance(item[0], str) or not isinstance(item[1], str):
                    raise ProductValidationError(
                        f"product file {fn} has invalid bug_links: {item!r}"
                    )

                # NOTE(willkg): This doesn't verify templates are well formed. That's
                # handled in a test in the code that uses the template.

            for item in json_data.get("product_home_links", []):
                if len(item) != 2:
                    raise ProductValidationError(
                        f"product file {fn} has invalid product_home_links: {item!r}"
                    )
                if not isinstance(item[0], str) or not isinstance(item[1], str):
                    raise ProductValidationError(
                        f"product file {fn} has invalid product_home_links: {item!r}"
                    )

            # Verify featured version data
            version_json_urls = json_data.get("version_json_urls", {})
            for version_url in version_json_urls.values():
                get_version_json_data(version_url)

            # Try to build a Product out of it
            Product(**json_data)

    except json.decoder.JSONDecodeError as jde:
        raise ProductValidationError(
            f"product file {fn} can not be decoded: {jde}"
        ) from jde

    except PermissionError as exc:
        raise ProductValidationError(
            f"product file {fn} cannot be opened: {exc}"
        ) from exc

    except TypeError as exc:
        raise ProductValidationError(
            f"product file {fn} has invalid fields/values: {exc}"
        ) from exc
