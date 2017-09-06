"""delete signature summaries

Revision ID: 07c6633fa1b6
Revises: afc2f95a298b
Create Date: 2017-08-31 17:33:19.969807

"""
from alembic import op
from socorro.lib.migrations import load_stored_proc

# revision identifiers, used by Alembic.
revision = '07c6633fa1b6'
down_revision = 'afc2f95a298b'


def upgrade():
    # Get a list of ALL tables that start with 'signature_summary_*'
    connection = op.get_bind()
    cursor = connection.connection.cursor()
    cursor.execute("""
        SELECT c.relname FROM pg_catalog.pg_class c
        WHERE c.relkind = 'r' AND c.relname LIKE 'signature_summary_%'
    """)
    all_table_names = []
    for records in cursor.fetchall():
        table_name, = records
        all_table_names.append(table_name)

    # Now delete all these massive tables.
    # But make sure that we drop them in the "right" order.
    # In particular we want to make sure we first drop
    # 'signature_summary_os_20130603' *before* we drop 'signature_summary_os'
    # since the former depends on the latter.
    all_table_names.sort(reverse=True)
    for table_name in all_table_names:
        op.execute('DROP TABLE IF EXISTS {}'.format(table_name))

    # Now delete all stored procedures
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_architecture(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_device(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_flash_version(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_graphics(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_installations(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_os(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_process_type(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_products(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_signature_summary_uptime(date, boolean)
    """)
    load_stored_proc(op, ['backfill_matviews.sql'])

    # Remove all mentions of signature_summary_* from the table that
    # handles making more partitions.
    op.execute("""
        DELETE FROM report_partition_info
        WHERE table_name LIKE 'signature_summary_%'
    """)


def downgrade():
    # There is no going back.
    pass
