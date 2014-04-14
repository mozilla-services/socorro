"""bug 812536 drop hang report

Revision ID: 389f5501023b
Revises: 2209ca57dcc6
Create Date: 2013-09-06 14:15:21.470498

"""

# revision identifiers, used by Alembic.
revision = '389f5501023b'
down_revision = '2209ca57dcc6'

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

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
    op.execute('DROP VIEW hang_report')
    op.drop_table(u'daily_hangs')
    op.execute('DROP FUNCTION update_hang_report(date, boolean, interval)')
    op.execute('DROP FUNCTION backfill_hang_report(date)')
    app_path=os.getcwd()
    procs = [
        'backfill_matviews.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        with open(myfile, 'r') as file:
            op.execute(file.read())


def downgrade():
    op.create_table(u'daily_hangs',
    sa.Column(u'browser_signature_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column(u'duplicates', postgresql.ARRAY(sa.TEXT()), autoincrement=False, nullable=True),
    sa.Column(u'flash_version_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column(u'hang_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column(u'plugin_signature_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column(u'plugin_uuid', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column(u'product_version_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column(u'report_date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column(u'url', CITEXT(), autoincrement=False, nullable=True),
    sa.Column(u'uuid', sa.TEXT(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint(u'plugin_uuid', name=u'daily_hangs_pkey')
    )
    op.execute("""
        CREATE VIEW hang_report AS
            SELECT product_versions.product_name AS product,
            product_versions.version_string AS version,
            browser_signatures.signature AS browser_signature,
            plugin_signatures.signature AS plugin_signature,
            daily_hangs.hang_id AS browser_hangid,
            flash_versions.flash_version,
            daily_hangs.url, daily_hangs.uuid,
            daily_hangs.duplicates,
            daily_hangs.report_date AS report_day
        FROM ((((daily_hangs JOIN product_versions USING (product_version_id))
        JOIN signatures browser_signatures ON
        ((daily_hangs.browser_signature_id = browser_signatures.signature_id)))
        JOIN signatures plugin_signatures ON
        ((daily_hangs.plugin_signature_id = plugin_signatures.signature_id)))
        LEFT JOIN flash_versions USING (flash_version_id))
    """)
    # Restore the functions for matviews manually
