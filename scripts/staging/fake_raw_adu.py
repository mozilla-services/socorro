#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import psycopg2
import psycopg2.extensions
import psycopg2.extras

#connect to CSD database
csd = psycopg2.connect("dbname=breakpad user=postgres port=5432")
csd_cur = csd.cursor()

# check if we already have ADU for the day
csd_cur.execute("""
    SELECT COUNT(*) FROM raw_adu WHERE "date" = 'yesterday'::date
""")

if csd_cur.fetchone()[0] > 0:
    sys.stderr.write('raw_adu has already been exported for yesterday\n')
    sys.exit(-1)

#dump raw_adu to file
csd_cur.execute("""
    INSERT into raw_adu
        (SELECT adu_count,
        'yesterday'::date as "date",
        product_name,
        product_os_platform,
        product_os_version,
        product_version,
        build,
        build_channel,
        product_guid,
        update_channel
        FROM raw_adu
        WHERE date in (select max(date) from raw_adu)
    )
""")
csd.commit()
csd.close()

print 'raw_adu successfully updated'

sys.exit(0)
