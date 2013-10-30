# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
migrations.py
Utility functions that work with Alembic
Includes classes that define custom types we use that aren't
defined in SQLAlchemy yet.
"""

import os


def load_stored_proc(op, filelist):
    """
    Takes a list of files and the alembic op object as arguments
    Load and run CREATE OR REPLACE function commands from files
    Expects files to be in:
        $CWD/socorro/external/postgresql/raw_sql/procs/
    """
    app_path=os.getcwd()
    for filename in filelist:
        sqlfile = app_path + '/socorro/external/postgresql/raw_sql/procs/' + filename
        with open(sqlfile, 'r') as stored_proc:
            op.execute(stored_proc.read())


def fix_permissions(op, tablename):
    """
    Takes a table name and an alembic op object as arguments
    Updates table permissions to make the table owned by breakpad_rw
    """
    op.execute("ALTER TABLE %s OWNER TO breakpad_rw" % tablename)
