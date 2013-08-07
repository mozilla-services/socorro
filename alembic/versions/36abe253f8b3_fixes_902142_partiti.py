"""Fixes 902142 partition matviews

Revision ID: 36abe253f8b3
Revises: 2645cb324bf4
Create Date: 2013-08-07 10:17:05.769404

"""

# revision identifiers, used by Alembic.
revision = '36abe253f8b3'
down_revision = '2645cb324bf4'

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column


class CITEXT(types.UserDefinedType):
    name = 'citext'

    def get_col_spec(self):
        return 'CITEXT'

    def bind_processor(self, dialect):
        return lambda value: value

    def result_processor(self, dialect, coltype):
        return lambda value: value

    def __repr__(self):
        return "citext"

class JSON(types.UserDefinedType):
    name = 'json'

    def get_col_spec(self):
        return 'JSON'

    def bind_processor(self, dialect):
        return lambda value: value

    def result_processor(self, dialect, coltype):
        return lambda value: value

    def __repr__(self):
        return "json"

def upgrade():
    op.add_column(u'report_partition_info', sa.Column(u'partition_column', sa.TEXT()))

    # Drop FK constraints on parent tables
    op.drop_constraint('signature_summary_architecture_product_version_id_fkey', 'signature_summary_architecture')
    op.drop_constraint('signature_summary_architecture_signature_id_fkey', 'signature_summary_architecture')
    op.drop_constraint('signature_summary_flash_version_product_version_id_fkey', 'signature_summary_flash_version')
    op.drop_constraint('signature_summary_flash_version_signature_id_fkey', 'signature_summary_flash_version')
    op.drop_constraint('signature_summary_installations_signature_id_fkey', 'signature_summary_installations')
    op.drop_constraint('signature_summary_os_product_version_id_fkey', 'signature_summary_os')
    op.drop_constraint('signature_summary_os_signature_id_fkey', 'signature_summary_os')
    op.drop_constraint('signature_summary_process_type_product_version_id_fkey', 'signature_summary_process_type')
    op.drop_constraint('signature_summary_process_type_signature_id_fkey', 'signature_summary_process_type')
    op.drop_constraint('signature_summary_products_product_version_id_fkey', 'signature_summary_products')
    op.drop_constraint('signature_summary_products_signature_id_fkey', 'signature_summary_products')
    op.drop_constraint('signature_summary_uptime_product_version_id_fkey', 'signature_summary_uptime')
    op.drop_constraint('signature_summary_uptime_signature_id_fkey', 'signature_summary_uptime')

    app_path=os.getcwd()
    procs = ['weekly_report_partitions.sql',
             'backfill_weekly_report_partitions.sql']
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        proc = open(myfile, 'r').read()
        op.execute(proc)
    # Now run this against the raw_crashes table
    op.execute("""
        UPDATE report_partition_info
        SET partition_column = 'date_processed'
    """)

    report_partition_info = table(u'report_partition_info',
        column(u'build_order', sa.INTEGER()),
        column(u'fkeys', postgresql.ARRAY(sa.TEXT())),
        column(u'indexes', postgresql.ARRAY(sa.TEXT())),
        column(u'keys', postgresql.ARRAY(sa.TEXT())),
        column(u'table_name', CITEXT()),
        column(u'partition_column', sa.TEXT()),
    )
    op.bulk_insert(report_partition_info, [
            {'table_name':  u'signature_summary_installations',
             'build_order': 5,
             'fkeys': ["(signature_id) REFERENCES signatures(signature_id)"],
             'partition_column': 'report_date',
             'keys': ["signature_id,product_name,version_string,report_date"],
             'indexes': ["report_date"],
            },
            {'table_name':  u'signature_summary_architecture',
             'build_order': 6,
             'fkeys': ["(signature_id) REFERENCES signatures(signature_id)", "(product_version_id) REFERENCES product_versions(product_version_id)"],
             'partition_column': 'report_date',
             'keys': ["signature_id, architecture, product_version_id, report_date"],
             'indexes': ["report_date"],
            },
            {'table_name':  u'signature_summary_flash_version',
             'build_order': 7,
             'fkeys': ["(signature_id) REFERENCES signatures(signature_id)", "(product_version_id) REFERENCES product_versions(product_version_id)"],
             'partition_column': 'report_date',
             'keys': ["signature_id, flash_version, product_version_id, report_date"],
             'indexes': ["report_date"],
            },
            {'table_name':  u'signature_summary_os',
             'build_order': 8,
             'fkeys': ["(signature_id) REFERENCES signatures(signature_id)", "(product_version_id) REFERENCES product_versions(product_version_id)"],
             'partition_column': 'report_date',
             'keys': ["signature_id, os_version_string, product_version_id, report_date"],
             'indexes': ["report_date"],
            },
            {'table_name':  u'signature_summary_process_type',
             'build_order': 9,
             'fkeys': ["(signature_id) REFERENCES signatures(signature_id)", "(product_version_id) REFERENCES product_versions(product_version_id)"],
             'partition_column': 'report_date',
             'keys': ["signature_id, process_type, product_version_id, report_date"],
             'indexes': ["report_date"],
            },
            {'table_name':  u'signature_summary_products',
             'build_order': 10,
             'fkeys': ["(signature_id) REFERENCES signatures(signature_id)", "(product_version_id) REFERENCES product_versions(product_version_id)"],
             'partition_column': 'report_date',
             'keys': ["signature_id, product_version_id, report_date"],
             'indexes': ["report_date"],
            },
            {'table_name':  u'signature_summary_uptime',
             'build_order': 11,
             'fkeys': ["(signature_id) REFERENCES signatures(signature_id)", "(product_version_id) REFERENCES product_versions(product_version_id)"],
             'partition_column': 'report_date',
             'keys': ["signature_id, uptime_string, product_version_id, report_date"],
             'indexes': ["report_date"],
            },
    ])

    op.alter_column(u'report_partition_info', u'partition_column',
               existing_type=sa.TEXT(),
               nullable=False)

    op.execute("""
        SELECT backfill_weekly_report_partitions('2013-06-03', '2013-08-12', 'signature_summary_architecture')
    """)
    op.execute("""
        SELECT backfill_weekly_report_partitions('2013-06-03', '2013-08-12', 'signature_summary_flash_version')
    """)
    op.execute("""
        SELECT backfill_weekly_report_partitions('2013-06-03', '2013-08-12', 'signature_summary_installations')
    """)
    op.execute("""
        SELECT backfill_weekly_report_partitions('2013-06-03', '2013-08-12', 'signature_summary_os')
    """)
    op.execute("""
        SELECT backfill_weekly_report_partitions('2013-06-03', '2013-08-12', 'signature_summary_process_type')
    """)
    op.execute("""
        SELECT backfill_weekly_report_partitions('2013-06-03', '2013-08-12', 'signature_summary_products')
    """)
    op.execute("""
        SELECT backfill_weekly_report_partitions('2013-06-03', '2013-08-12', 'signature_summary_uptime')
    """)

def downgrade():
    op.execute("""
        DELETE from report_partition_info
        WHERE table_name ~ '^signature_summary_'
    """)
    op.drop_column(u'report_partition_info', u'partition_column')

    # Drop all child tables (?)
    op.execute("""
        DO  $$DECLARE mytable record;
        BEGIN
            FOR mytable IN SELECT relname FROM pg_class
                WHERE relname ~ '^signature_summary_*201*' and relkind = 'r'
            LOOP
                EXECUTE 'DROP TABLE ' || quote_ident(mytable.relname) || ' CASCADE';
            END LOOP;
        END$$
    """)

    # Drop FK constraints on parent tables
    op.create_foreign_key('signature_summary_architecture_product_version_id_fkey', 'signature_summary_architecture', 'product_versions', ["product_version_id"], ["product_version_id"])
    op.create_foreign_key('signature_summary_architecture_signature_id_fkey', 'signature_summary_architecture', 'signatures', ["signature_id"], ["signature_id"])
    op.create_foreign_key('signature_summary_flash_version_product_version_id_fkey', 'signature_summary_flash_version', 'product_versions', ["product_version_id"], ["product_version_id"])
    op.create_foreign_key('signature_summary_flash_version_signature_id_fkey', 'signature_summary_flash_version', 'signatures', ["signature_id"], ["signature_id"])
    op.create_foreign_key('signature_summary_installations_signature_id_fkey', 'signature_summary_installations', 'signatures', ["signature_id"], ["signature_id"])
    op.create_foreign_key('signature_summary_os_product_version_id_fkey', 'signature_summary_os', 'product_versions', ["product_version_id"], ["product_version_id"])
    op.create_foreign_key('signature_summary_os_signature_id_fkey', 'signature_summary_os', 'signatures', ["signature_id"], ["signature_id"])
    op.create_foreign_key('signature_summary_process_type_product_version_id_fkey', 'signature_summary_process_type', 'product_versions', ["product_version_id"], ["product_version_id"])
    op.create_foreign_key('signature_summary_process_type_signature_id_fkey', 'signature_summary_process_type', 'signatures', ["signature_id"], ["signature_id"])
    op.create_foreign_key('signature_summary_products_product_version_id_fkey', 'signature_summary_products', 'product_versions', ["product_version_id"], ["product_version_id"])
    op.create_foreign_key('signature_summary_products_signature_id_fkey', 'signature_summary_products', 'signatures', ["signature_id"], ["signature_id"])
    op.create_foreign_key('signature_summary_uptime_product_version_id_fkey', 'signature_summary_uptime', 'product_versions', ["product_version_id"], ["product_version_id"])
    op.create_foreign_key('signature_summary_uptime_signature_id_fkey', 'signature_summary_uptime', 'signatures', ["signature_id"], ["signature_id"])
