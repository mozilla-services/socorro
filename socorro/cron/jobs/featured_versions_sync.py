import requests

from configman import Namespace
from crontabber.base import BaseCronApp
from crontabber.mixins import with_postgres_transactions

from socorro.external.postgresql.dbapi2_util import single_value_sql


@with_postgres_transactions()
class FeaturedVersionsSyncCronApp(BaseCronApp):
    app_name = 'featured-versions-sync'
    app_description = """Use the public web API to find out what
    versions are featured on crash-stats.mozilla.com (configurable).
    """

    required_config = Namespace()
    required_config.add_option(
        'api_endpoint_url',
        default=(
            'https://crash-stats.mozilla.com/api/ProductVersions/?'
            'active=true&is_featured=true',
        ),
        doc='URL from which we can download all the active products'
    )

    def run(self):
        hits = requests.get(self.config.api_endpoint_url).json()['hits']
        featured_products = {}
        for pv in hits:
            if pv['product'] not in featured_products:
                featured_products[pv['product']] = []
            assert pv['is_featured']
            featured_products[pv['product']].append(pv['version'])

        for product, versions in featured_products.items():
            if versions:
                self.database_transaction_executor(
                    self.edit_featured_versions,
                    product,
                    featured_products[product]
                )

    def edit_featured_versions(self, connection, product, versions):
        sql = """
            SELECT
                edit_featured_versions(%s, {})
        """.format(','.join('%s' for _ in versions))
        worked = single_value_sql(
            connection,
            sql,
            [product] + versions
        )
        if worked:
            self.config.logger.info(
                'Set featured versions for %s %r' % (
                    product,
                    versions
                )
            )
        else:
            self.config.logger.warning(
                'Unable to set featured versions for %s %r' % (
                    product,
                    versions
                )
            )
