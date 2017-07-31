"""remove product_info view

Revision ID: 15d9132d759e
Revises: a5e0f0bc87d6
Create Date: 2017-07-31 09:30:06.667346

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '15d9132d759e'
down_revision = 'a5e0f0bc87d6'


def upgrade():
    op.execute('DROP VIEW default_versions_builds')
    op.execute('DROP VIEW versions_builds')
    op.execute('DROP VIEW product_info')


def downgrade():
    op.execute("""
    CREATE VIEW product_info AS
    SELECT product_versions.product_version_id,
           product_versions.product_name,
           product_versions.version_string,
           'new'::text AS which_table,
           product_versions.build_date AS start_date,
           product_versions.sunset_date AS end_date,
           product_versions.featured_version AS is_featured,
           product_versions.build_type,
           ((product_release_channels.throttle * (100)::numeric))::numeric(5,2) AS throttle,
           product_versions.version_sort,
           products.sort AS product_sort,
           release_channels.sort AS channel_sort,
           product_versions.has_builds,
           product_versions.is_rapid_beta
    FROM ( ( ( product_versions
              JOIN product_release_channels ON ( ( ( product_versions.product_name = product_release_channels.product_name )
                                                  AND ( product_versions.build_type = product_release_channels.release_channel ) ) ) )
            JOIN products ON ( ( product_versions.product_name = products.product_name ) ) )
          JOIN release_channels ON ( ( product_versions.build_type = release_channels.release_channel ) ) )
    ORDER BY product_versions.product_name,
             product_versions.version_string;
    """)
    op.execute("""
    CREATE VIEW default_versions_builds AS
        SELECT count_versions.product_name, count_versions.version_string, count_versions.product_version_id FROM (SELECT product_info.product_name, product_info.version_string, product_info.product_version_id, row_number() OVER (PARTITION BY product_info.product_name ORDER BY ((('now'::text)::date >= product_info.start_date) AND (('now'::text)::date <= product_info.end_date)) DESC, product_info.is_featured DESC, product_info.channel_sort DESC) AS sort_count FROM product_info WHERE product_info.has_builds) count_versions WHERE (count_versions.sort_count = 1)
    """)
    op.execute("""
    CREATE VIEW default_versions AS
    SELECT count_versions.product_name, count_versions.version_string, count_versions.product_version_id FROM (SELECT product_info.product_name, product_info.version_string, product_info.product_version_id, row_number() OVER (PARTITION BY product_info.product_name ORDER BY ((('now'::text)::date >= product_info.start_date) AND (('now'::text)::date <= product_info.end_date)) DESC, product_info.is_featured DESC, product_info.channel_sort DESC) AS sort_count FROM product_info) count_versions WHERE (count_versions.sort_count = 1)
    """)
