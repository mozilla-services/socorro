#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import psycopg2, psycopg2.extensions

conn = psycopg2.connect("dbname=breakpad user=postgres")

conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()

cur.execute("""
   select relname from pg_stat_user_tables
      where relname like 'extensions_20%%'
      order by relname
   """ )

partitions = [ x for ( x, ) in cur.fetchall() ]

for partition in partitions:
   index_name = "%s_extension_id_extension_version_idx" % partition

   cur.execute("DROP INDEX %s" % ( index_name, ) )
   print "%s dropped." % index_name
