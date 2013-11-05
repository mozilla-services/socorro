"""Fixes bug 933963 Split up Signature Summary jobs

Revision ID: 477e1c6e6df3
Revises: 317e15fbf13a
Create Date: 2013-11-01 15:45:34.884331

"""

# revision identifiers, used by Alembic.
revision = '477e1c6e6df3'
down_revision = '18b22de09433'

from alembic import op
from socorro.lib import citexttype, jsontype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    load_stored_proc(op, [
        'backfill_named_table.sql',
        'update_signature_summary_architecture.sql',
        'update_signature_summary_device.sql',
        'update_signature_summary_flash_version.sql',
        'update_signature_summary_installations.sql',
        'update_signature_summary_os.sql',
        'update_signature_summary_process_type.sql',
        'update_signature_summary_products.sql',
        'update_signature_summary_uptime.sql'
    ])

    op.execute("""
        DROP FUNCTION IF EXISTS update_signature_summary_devices(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS backfill_signature_summary_devices(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS backfill_signature_summary_graphics(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS update_signature_summary(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS backfill_signature_summary(date, boolean)
    """)

def downgrade():
    for i in [
        'backfill_named_table(text, date)',
        'update_signature_summary_architecture(date, boolean)',
        'update_signature_summary_device(date, boolean)',
        'update_signature_summary_flash_version(date, boolean)',
        'update_signature_summary_installations(date, boolean)',
        'update_signature_summary_os(date, boolean)',
        'update_signature_summary_process_type(date, boolean)',
        'update_signature_summary_products(date, boolean)',
        'update_signature_summary_uptime(date, boolean)'
    ]:
        op.execute(""" DROP FUNCTION  %s """ % i)

    load_stored_proc(op, [
        'backfill_signature_summary.sql',
        'update_signature_summary.sql',
        'update_signature_summary_devices.sql',
        'backfill_signature_summary_devices.sql',
        'backfill_signature_summary_graphics.sql',
    ])
