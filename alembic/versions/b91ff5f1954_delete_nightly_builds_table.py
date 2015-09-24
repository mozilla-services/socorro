"""delete nightly_builds table

Revision ID: b91ff5f1954
Revises: 16b2bee7db72
Create Date: 2015-09-11 15:01:30.509337

"""

# revision identifiers, used by Alembic.
revision = 'b91ff5f1954'
down_revision = '16b2bee7db72'

from alembic import op


def upgrade():
    op.execute("""
        DROP TABLE nightly_builds
    """)
    op.execute('COMMIT')


def downgrade():
    # the primary purpose of the downgrade is for the sake of Travis :)
    op.execute("""
        CREATE TABLE nightly_builds (
            product_version_id integer NOT NULL,
            build_date date NOT NULL,
            report_date date NOT NULL,
            days_out integer NOT NULL,
            report_count integer DEFAULT 0 NOT NULL
        )
    """)
    op.execute("""
        ALTER TABLE ONLY nightly_builds
            ADD CONSTRAINT nightly_builds_key
            PRIMARY KEY (product_version_id, build_date, days_out)
    """)
    op.execute("""
        CREATE INDEX nightly_builds_product_version_id_report_date
        ON nightly_builds USING btree (product_version_id, report_date)
    """)
    op.execute('COMMIT')
