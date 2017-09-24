"""drop plugins_reports tables

Revision ID: a38b03765a79
Revises: ae2c8ff8c073
Create Date: 2017-09-08 13:23:44.142686

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'a38b03765a79'
down_revision = 'ae2c8ff8c073'


def upgrade():
    # Get a list of ALL tables that start with 'signature_summary_*'
    connection = op.get_bind()
    cursor = connection.connection.cursor()
    cursor.execute("""
        SELECT c.relname FROM pg_catalog.pg_class c
        WHERE c.relkind = 'r' AND c.relname LIKE 'plugins_reports_%'
    """)
    all_table_names = []
    for records in cursor.fetchall():
        table_name, = records
        all_table_names.append(table_name)

    # Now delete all these tables.
    # But make sure that we drop them in the "right" order.
    # In particular we want to make sure we first drop
    # 'plugins_reports_20170227' *before* we drop 'plugins_reports'
    # since the former depends on the latter.
    all_table_names.sort(reverse=True)
    for table_name in all_table_names:
        op.execute('DROP TABLE IF EXISTS {}'.format(table_name))

    # Remove all mentions of signature_summary_* from the table that
    # handles making more partitions.
    op.execute("""
        DELETE FROM report_partition_info
        WHERE table_name LIKE 'plugins_reports_%'
    """)


def downgrade():
    # There is no going back.
    pass
