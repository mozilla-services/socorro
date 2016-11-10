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
import warnings


def get_local_filepath(filename):
    """
    Helper for finding our raw SQL files locally.

    Expects files to be in:
        $SOCORRO_PATH/socorro/external/postgresql/raw_sql/procs/
    """
    procs_dir = os.path.normpath(os.path.join(
        __file__,
        '../../',
        'external/postgresql/raw_sql/procs'
    ))
    return os.path.join(procs_dir, filename)


def load_stored_proc(op, filelist):
    """
    Takes the alembic op object as arguments and a list of files as arguments
    Load and run CREATE OR REPLACE function commands from files
    """
    for filename in filelist:
        sqlfile = get_local_filepath(filename)
        # Capturing "file not exists" here rather than allowing
        # an exception to be thrown. Some of the rollback scripts
        # would otherwise throw unhelpful exceptions when a SQL
        # file is removed from the repo.
        if not os.path.isfile(sqlfile):
            warnings.warn(
                "Did not find %r. Continuing migration." % sqlfile,
                UserWarning,
                2
            )
            continue
        with open(sqlfile, 'r') as stored_proc:
            op.execute(stored_proc.read())


def fix_permissions(op, tablename):
    """
    Takes a table name and an alembic op object as arguments
    Updates table permissions to make the table owned by breakpad_rw
    """
    op.execute("ALTER TABLE %s OWNER TO breakpad_rw" % tablename)
