"""bug 902839 add version_string to signature_summary* tables

Revision ID: 35604f61bc24
Revises: 36abe253f8b3
Create Date: 2013-08-12 14:37:51.046982

"""

# revision identifiers, used by Alembic.
revision = '35604f61bc24'
down_revision = '36abe253f8b3'

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
    op.add_column(u'signature_summary_architecture', sa.Column(u'version_string', sa.TEXT()))
    op.add_column(u'signature_summary_flash_version', sa.Column(u'version_string', sa.TEXT()))
    op.add_column(u'signature_summary_os', sa.Column(u'version_string', sa.TEXT()))
    op.add_column(u'signature_summary_process_type', sa.Column(u'version_string', sa.TEXT()))
    op.add_column(u'signature_summary_uptime', sa.Column(u'version_string', sa.TEXT()))
    op.execute("""
        UPDATE signature_summary_architecture
            SET version_string = product_versions.version_string
        FROM product_versions
        WHERE product_versions.product_version_id = signature_summary_architecture.product_version_id
    """)
    op.execute("""
        UPDATE signature_summary_flash_version
            SET version_string = product_versions.version_string
        FROM product_versions
        WHERE product_versions.product_version_id = signature_summary_flash_version.product_version_id
    """)
    op.execute("""
        UPDATE signature_summary_os
            SET version_string = product_versions.version_string
        FROM product_versions
        WHERE product_versions.product_version_id = signature_summary_os.product_version_id
    """)
    op.execute("""
        UPDATE signature_summary_process_type
            SET version_string = product_versions.version_string
        FROM product_versions
        WHERE product_versions.product_version_id = signature_summary_process_type.product_version_id
    """)
    op.execute("""
        UPDATE signature_summary_uptime
            SET version_string = product_versions.version_string
        FROM product_versions
        WHERE product_versions.product_version_id = signature_summary_uptime.product_version_id
    """)
    op.alter_column(u'signature_summary_architecture', u'version_string', nullable=False)
    op.alter_column(u'signature_summary_flash_version', u'version_string', nullable=False)
    op.alter_column(u'signature_summary_os', u'version_string', nullable=False)
    op.alter_column(u'signature_summary_process_type', u'version_string', nullable=False)
    op.alter_column(u'signature_summary_uptime', u'version_string', nullable=False)
    app_path=os.getcwd()
    procs = [
        'update_signature_summary.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        with open(myfile, 'r') as file:
            op.execute(file.read())


def downgrade():
    op.drop_column(u'signature_summary_uptime', u'version_string')
    op.drop_column(u'signature_summary_process_type', u'version_string')
    op.drop_column(u'signature_summary_os', u'version_string')
    op.drop_column(u'signature_summary_flash_version', u'version_string')
    op.drop_column(u'signature_summary_architecture', u'version_string')

    ## NOTE: Be sure to restore old update_signature_summary.sql if this is backed out!!

