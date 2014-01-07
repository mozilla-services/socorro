"""Fixes bug 915162 update releases procs

Revision ID: 1ade2c09799b
Revises: 58d0dc2f6aa4
Create Date: 2014-01-03 16:53:18.062523

"""

# revision identifiers, used by Alembic.
revision = '1ade2c09799b'
down_revision = '58d0dc2f6aa4'

from alembic import op
from socorro.lib import citexttype, jsontype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op,
       ['001_update_reports_clean.sql',
        'add_new_product.sql',
        'add_new_release.sql',
        'edit_product_info.sql',
        'reports_clean_weekly_partition.sql',
        'sunset_date.sql',
        'update_adu.sql',
        'update_build_adu.sql',
        'update_product_versions.sql'
        ]
    )

def downgrade():
    load_stored_proc(op,
       ['001_update_reports_clean.sql',
        'add_new_product.sql',
        'add_new_release.sql',
        'edit_product_info.sql',
        'reports_clean_weekly_partition.sql',
        'sunset_date.sql',
        'update_adu.sql',
        'update_build_adu.sql',
        'update_product_versions.sql'
        ]
    )
