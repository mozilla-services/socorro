#!/usr/bin/env python

import codecs
import datetime
import optparse
import os
import pyhs2
import tempfile
import unicodedata
import urllib2

# Example command-line usage:
# $ . /etc/socorro/socorrorc
# $ $PYTHON hive_adi_test.py -d '2015-01-21' -s peach-gw.peach.metrics.scl3.mozilla.com -o /tmp/output_adi.txt

def main():

    storage_date = datetime.date.today().isoformat()

    # Defaulting to creating a temp file for output
    raw_adi_logs_pathname = os.path.join(
        tempfile.gettempdir(),
        "%s.raw_adi_logs.TEMPORARY%s" % (
            storage_date,
            '.txt'
        )
    )

    p = optparse.OptionParser()
    p.add_option('--target-date', '-d', default=storage_date)
    p.add_option('--host', '-s', default='localhost')
    p.add_option('--user', '-u', default='socorro')
    p.add_option('--output-filename', '-o', default=raw_adi_logs_pathname)
    options, arguments = p.parse_args()

    query = """

        select
            ds,
            split(request_url,'/')[5],
            split(split(request_url,'/')[10], '%%20')[0],
            split(split(request_url,'/')[10], '%%20')[1],
            split(request_url,'/')[4],
            split(request_url,'/')[6],
            split(request_url,'/')[9],
            split(request_url,'/')[3],
            count(*)
        FROM v2_raw_logs
        WHERE
            (domain='addons.mozilla.org' OR domain='blocklist.addons.mozilla.org')
            and http_status_code = '200'
            and request_url like '/blocklist/3/%%'
            and ds='%s'
        GROUP BY
            ds,
            split(request_url,'/')[5],
            split(split(request_url,'/')[10], '%%20')[0],
            split(split(request_url,'/')[10], '%%20')[1],
            split(request_url,'/')[4],
            split(request_url,'/')[6],
            split(request_url,'/')[9],
            split(request_url,'/')[3]
    """

    hive = pyhs2.connect(
        host=options.host,
        port=10000,
        authMechanism='PLAIN',
        user=options.user,
        password='ignored',
        database='default',
        # the underlying TSocket setTimeout() wants milliseconds
        timeout=30 * 60 * 1000
    )

    def remove_control_characters(s):
        if isinstance(s, str):
            s = unicode(s, 'utf-8', errors='replace')
        return ''.join(c for c in s if unicodedata.category(c)[0] != "C")

    with codecs.open(options.output_filename, 'w', 'utf-8') as f:
        cur = hive.cursor()
        query = query % options.target_date
        cur.execute(query)
        for row in cur:
            if None in row:
                continue
            f.write(
                "\t"
                .join(
                    remove_control_characters(
                        urllib2.unquote(v)
                    ).replace('\\', '\\\\')
                    if isinstance(v, basestring) else str(v)
                    for v in row
                )
            )
            f.write("\n")

if __name__ == '__main__':
    main()
