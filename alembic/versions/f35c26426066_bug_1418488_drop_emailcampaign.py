"""bug 1418488 drop emailcampaign

Revision ID: f35c26426066
Revises: 77856f165be7
Create Date: 2017-11-17 21:36:39.418681

"""

# revision identifiers, used by Alembic.
revision = 'f35c26426066'
down_revision = '77856f165be7'

from alembic import op
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute("""
        DROP TABLE IF EXISTS
        email_campaigns_contacts
    """)
    op.execute("""
        DROP TABLE IF EXISTS
        email_campaigns
    """)
    op.execute("""
        DROP TABLE IF EXISTS
        email_contacts
    """)


def downgrade():
    # NOTE(willkg): This doesn't reconstitute the data--just recreates the tables.
    op.execute("""
    CREATE TABLE email_campaigns (
        author TEXT NOT NULL,
        body TEXT NOT NULL,
        date_created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        email_count INTEGER DEFAULT 0,
        end_date TIMESTAMP WITH TIME ZONE NOT NULL,
        id SERIAL NOT NULL,
        product TEXT NOT NULL,
        signature TEXT NOT NULL,
        start_date TIMESTAMP WITH TIME ZONE NOT NULL,
        status TEXT DEFAULT 'stopped' NOT NULL,
        subject TEXT NOT NULL,
        versions TEXT NOT NULL,
        PRIMARY KEY (id)
    )
    """)
    op.execute("""
    CREATE TABLE email_contacts (
        crash_date TIMESTAMP WITH TIME ZONE,
        email TEXT NOT NULL,
        id SERIAL NOT NULL,
        ooid TEXT,
        subscribe_status BOOLEAN DEFAULT True,
        subscribe_token TEXT NOT NULL,
        PRIMARY KEY (id)
    )
    """)
    op.execute("""
    CREATE TABLE email_campaigns_contacts (
        email_campaigns_id INTEGER,
        email_contacts_id INTEGER,
        status TEXT DEFAULT 'stopped' NOT NULL,
        FOREIGN KEY(email_campaigns_id) REFERENCES email_campaigns (id),
        FOREIGN KEY(email_contacts_id) REFERENCES email_contacts (id)
    )
    """)
