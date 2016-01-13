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
        default='https://crash-stats.mozilla.com/api/CurrentProducts/',
        doc='URL from which we can download all the current products'
    )

    def run(self):
        hits = requests.get(self.config.api_endpoint_url).json()['hits']
        featured_products = dict(
            (product, [x['version'] for x in versions if x['featured']])
            for product, versions in hits.items()
        )
        for product in featured_products:
            versions = featured_products[product]
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
        assert single_value_sql(
            connection,
            sql,
            [product] + versions
        )
