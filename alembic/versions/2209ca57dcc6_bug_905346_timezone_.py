"""bug 905346 timezone fixes for existing tables

Revision ID: 2209ca57dcc6
Revises: 4de11772649b
Create Date: 2013-09-03 13:30:20.727845

"""

# revision identifiers, used by Alembic.
revision = '2209ca57dcc6'
down_revision = '4de11772649b'

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
    op.execute( "COMMIT" )

    for date_range in ('2011', '2012', '201301', '201302', '201303', '201304',
            '201305', '201306', '201307'):
        op.execute("BEGIN")
        op.execute("""
            DO $$
                DECLARE myrecord record;
                DECLARE theweek text;
            BEGIN
                FOR myrecord IN SELECT relname, conname from pg_constraint
                    JOIN pg_class ON pg_constraint.conrelid = pg_class.oid
                    WHERE consrc ~ 'without' and split_part(relname, '_%(date_range)s', 1)
                    IN (select table_name from report_partition_info
                        WHERE partition_column = 'date_processed'
                        UNION
                        select 'reports_clean' -- not in report_partition_info
                        UNION
                        select 'reports_user_info' -- not in report_partition_info
                        )
                LOOP
                    EXECUTE 'ALTER TABLE ' || quote_ident(myrecord.relname)
                        || ' DROP CONSTRAINT IF EXISTS '
                        || quote_ident(myrecord.conname) || ';';

                    theweek = substring(myrecord.relname from '........$');

                    EXECUTE 'ALTER TABLE ' || quote_ident(myrecord.relname)
                        || ' ADD CONSTRAINT ' || quote_ident(myrecord.conname)
                        || ' CHECK ((date_processed >= timestamptz('
                        || quote_literal(to_char(date(theweek), 'YYYY-MM-DD')) || '))'
                        || ' AND (date_processed < timestamptz('
                        || quote_literal(to_char(date(theweek) + 7, 'YYYY-MM-DD'))
                        || ')));';

                    RAISE NOTICE 'DONE: %%', myrecord.relname;
                END LOOP;
            END$$;
            """ % {'date_range': date_range})
        op.execute("COMMIT")
        op.execute("BEGIN")
        op.execute("""
            DO $$
                DECLARE myrecord record;
                DECLARE theweek text;
            BEGIN
                FOR myrecord IN SELECT relname, conname from pg_constraint
                    JOIN pg_class ON pg_constraint.conrelid = pg_class.oid
                    WHERE consrc ~ 'without' and split_part(relname, '_%(date_range)s', 1)
                    IN (select table_name from report_partition_info
                        WHERE partition_column = 'report_date')
                LOOP
                    EXECUTE 'ALTER TABLE ' || quote_ident(myrecord.relname)
                        || ' DROP CONSTRAINT IF EXISTS '
                        || quote_ident(myrecord.conname) || ';';

                    theweek = substring(myrecord.relname from '........$');

                    EXECUTE 'ALTER TABLE ' || quote_ident(myrecord.relname)
                        || ' ADD CONSTRAINT ' || quote_ident(myrecord.conname)
                        || ' CHECK ((report_date >= date('
                        || quote_literal(to_char(date(theweek), 'YYYY-MM-DD')) || '))'
                        || ' AND (report_date < date('
                        || quote_literal(to_char(date(theweek) + 7, 'YYYY-MM-DD'))
                        || ')));';

                    RAISE NOTICE 'DONE: %%', myrecord.relname;
                END LOOP;
            END$$;
            """ % {'date_range': date_range})
        op.execute("COMMIT")

def downgrade():
    """ NO GOING BACK """
    print "No Going Back"
