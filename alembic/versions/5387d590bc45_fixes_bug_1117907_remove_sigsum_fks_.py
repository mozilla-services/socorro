"""Fixes bug 1117907 - remove sigsum FKs, indexes

Revision ID: 5387d590bc45
Revises: 235c80dc2e12
Create Date: 2015-01-05 11:48:06.829452

"""

# revision identifiers, used by Alembic.
revision = '5387d590bc45'
down_revision = '235c80dc2e12'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    # search for signature_summary indexes and drop them
    op.execute("""
        -- Fixes bug 1117907
        DO $$
        declare
          r record;
        BEGIN
              FOR r IN
                select indexrelname
                  from pg_stat_user_indexes
                  where indexrelname ~ 'signature_summary_' and indexrelname !~ '_pkey'
                  LOOP
                      EXECUTE 'DROP INDEX ' || quote_ident(r.indexrelname);
                  END LOOP;
        END$$
    """)
    # search for signature_summary foreign keys and drop them
    op.execute("""
        -- Fixes bug 1117907
        DO $$
        DECLARE
            r record;
        BEGIN
            FOR r IN
                WITH tables as ( select relname, oid from pg_class where relname ~ 'signature_summary_' and relkind = 'r' )
                select conname, tables.relname as relname
                    from pg_constraint JOIN tables ON tables.oid = pg_constraint.conrelid
                    where contype = 'f' and conname ~ 'signature_summary_'
                LOOP
                    EXECUTE 'ALTER TABLE ' || quote_ident(r.relname) || ' DROP CONSTRAINT ' || quote_ident(r.conname);
                END LOOP;
        END$$
    """)
    # Remove creation of these from report_partition_info
    op.execute("""
        -- Fixes bug 1117907
        UPDATE report_partition_info SET fkeys = '{}'
        WHERE table_name ~ 'signature_summary_'
    """)

def downgrade():
    # Not going to restore them, change already made in models.py to remove
    pass
