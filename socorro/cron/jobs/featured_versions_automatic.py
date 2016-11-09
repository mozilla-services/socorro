import re

import requests

from configman import Namespace
from configman.converters import list_converter
from crontabber.base import BaseCronApp
from crontabber.mixins import (
    with_postgres_transactions,
    with_single_postgres_transaction,
)


def alias_list_to_dict(input_string):
    """Return a dict by splitting the input string by ','
    and splitting each item by a ':' to make it key and value.

    For example::

        >>> alias_list_to_dict('foo: bar, other:thing, ')
        {'foo': 'bar', 'other': 'thing'}

    """
    aliases = {}
    for item in input_string.split(','):
        if not item.strip():
            continue
        key, value = item.split(':')
        aliases[key.strip()] = value.strip()
    return aliases


class DownloadError(Exception):
    """when downloading a network resource fails"""


@with_postgres_transactions()
@with_single_postgres_transaction()
class FeaturedVersionsAutomaticCronApp(BaseCronApp):
    app_name = 'featured-versions-automatic'
    app_description = """Use https://product-details.mozilla.org/1.0/
    to automatically figure out what product versions should be
    set as featured.
    """

    required_config = Namespace()
    required_config.add_option(
        'api_endpoint_url',
        default=(
            'https://product-details.mozilla.org/1.0/{product}_versions.json'
        ),
        doc='URL from which we can download all the featured versions'
    )
    required_config.add_option(
        'products',
        default='firefox,mobile,thunderbird',
        from_string_converter=list_converter,
        doc='a comma-delimited list of products to recognize'
    )
    required_config.add_option(
        'aliases',
        default='mobile:FennecAndroid',
        from_string_converter=alias_list_to_dict,
        doc=(
            'a comma-delimited list of name:RealName. If a product '
            'does not need an alias match it by capitalizing the name '
            '(e.g. "thunderbird" -> "Thunderbird")'
        )
    )

    def run(self, connection):
        # The @with_single_postgres_transaction decorator makes
        # sure this cursor is committed or rolled back and cleaned up.
        cursor = connection.cursor()

        for product in self.config.products:
            url = self.config.api_endpoint_url.format(product=product)
            response = requests.get(url)
            if response.status_code != 200:
                raise DownloadError(
                    '{} ({})'.format(
                        url,
                        response.status_code,
                    )
                )
            versions = response.json()
            self._set_featured_versions(
                cursor,
                product,
                versions,
            )

    def _set_featured_versions(self, cursor, product, versions):
        # 'product_name' is what it's called in our product_versions
        # table.
        product_name = self.config.aliases.get(
            product,
            product.capitalize()
        )
        featured = set()
        if product_name == 'Firefox':
            featured.add(versions['FIREFOX_NIGHTLY'])
            featured.add(versions['FIREFOX_AURORA'])
            featured.add(versions['LATEST_FIREFOX_VERSION'])
            beta = versions['LATEST_FIREFOX_DEVEL_VERSION']
            # If the beta version is something like '59.0b12'
            # then convert that to '59.0b' which is basically right-stripping
            # any numbers after the 'b'.
            beta = re.sub('b(\d+)$', 'b', beta)
            featured.add(beta)
        elif product_name == 'FennecAndroid':
            featured.add(versions['nightly_version'])
            featured.add(versions['alpha_version'])
            featured.add(versions['beta_version'])
            featured.add(versions['version'])
        elif product_name == 'Thunderbird':
            featured.add(versions['LATEST_THUNDERBIRD_DEVEL_VERSION'])
            featured.add(versions['LATEST_THUNDERBIRD_ALPHA_VERSION'])
            featured.add(versions['LATEST_THUNDERBIRD_VERSION'])
            featured.add(versions['LATEST_THUNDERBIRD_NIGHTLY_VERSION'])
        else:
            raise NotImplementedError(product_name)

        # Remove all previous featured versions
        cursor.execute("""
            UPDATE product_versions
            SET featured_version = false
            WHERE featured_version = true AND product_name = %s
        """, (product_name,))
        cursor.execute("""
            UPDATE product_versions
            SET featured_version = true
            WHERE product_name = %s AND version_string IN %s
        """, (product_name, tuple(featured)))

        self.config.logger.info(
            'Set featured versions for {} to: {}'.format(
                product_name,
                ', '.join(sorted(featured)),
            )
        )
