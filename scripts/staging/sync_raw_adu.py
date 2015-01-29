#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# In production on stage db

import os
from os.path import join, getsize
import sys
import psycopg2
import psycopg2.extensions
import psycopg2.extras

#connect to CSD database
csd = psycopg2.connect("dbname=breakpad user=postgres port=5432")
csd_cur = csd.cursor()
# check if we already have ADU for the day
csd_cur.execute("""SELECT COUNT(*) FROM raw_adi WHERE "date" = 'yesterday'::date""")

if (csd_cur.fetchone()[0]) > 0:
    sys.stderr.write('raw_adi has already been exported for yesterday')
    sys.exit(-1)

#connect to replayDB
replay = psycopg2.connect("dbname=breakpad user=postgres port=5499")
rep_cur = replay.cursor()

# check if we already have ADU for the day
rep_cur.execute("""SELECT count(*) FROM raw_adi WHERE "date" = 'yesterday'::date""")

if (rep_cur.fetchone()[0]) == 0:
    sys.stderr.write('no raw_adi in replayDB for yesterday')
    sys.exit(-2)

#dump raw_adi to file
rep_cur.execute("""COPY ( SELECT * FROM raw_adi WHERE "date" = 'yesterday'::date )
TO '/tmp/raw_adi_update.csv' with csv;""")
replay.close()

#import raw_adi into CSD
csd_cur.execute("""COPY raw_adi FROM '/tmp/raw_adi_update.csv' with csv;""")
csd.commit()
csd.close()

print 'raw_adi successfully updated'

sys.exit(0)
