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
    SELECT COUNT(*) FROM raw_adi WHERE "date" = 'yesterday'::date
""")

if csd_cur.fetchone()[0] > 0:
    sys.stderr.write('raw_adi has already been exported for yesterday\n')
    sys.exit(-1)

#dump raw_adi from previous day and reinsert faked data
csd_cur.execute("""
    INSERT into raw_adi (
        adi_count,
        date,
        product_name,
        product_os_platform,
        product_os_version,
        product_version,
        build,
        product_guid,
        update_channel
    )
    (
        SELECT adi_count,
        'yesterday'::date as "date",
        product_name,
        product_os_platform,
        product_os_version,
        product_version,
        build,
        product_guid,
        update_channel
        FROM raw_adi
        WHERE date in (select max(date) from raw_adi)
    )
""")
csd.commit()
csd.close()

print 'raw_adi successfully updated'

sys.exit(0)
