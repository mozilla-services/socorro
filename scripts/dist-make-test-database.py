#!/usr/bin/python
#
# This file requires:
#   psycopg2 (python postgres driver)
#   postgres-dev package (on some systems)
#
# If you ran the installer for the webapp you should already meet these
# requirements.
#
# File to import data based on some random strings in the lists below 
# in conjuncture with a sample test file from:
#   http://people.mozilla.org/~morgamic/test-crashes.tar.gz
#
# If you want to use this correctly you'll need to download the file above and
# use the socorro schema found at:
#   http://socorro.googlecode.com/svn/trunk/webapp/socorro/models/socorro.sql
#
# Since you're looking at this, it means you probably also want to do some load
# testing.  If so, you will also want to add partitions using:
#   http://socorro.googlecode.com/svn/trunk/webapp/socorro/models/partitions.plpgsql
#
# Usage:
#   python make-test-database.py test-crashes.csv '2007-04-27 22:00:00' 1800000
#   (inserts 1800000 rows of random test data into the april 2007 table)
#
# Questions or flames - morgamic on irc.mozilla.org
#
# Note:
#   There is probably a prettier way to write this, it is a DirtyHack++ so if
#   you have advice, let me know! :)

import sys
import os
import psycopg2
from random import randint, choice
from datetime import datetime, timedelta
import time
from optparse import OptionParser
import re

o = OptionParser(usage="usage: dist-make-test-database.py dbname crashes.csv 1000010", add_help_option=False)

def store_date(option, opt_str, value, parser):
    setattr(parser, option.dest,
            datetime(*(time.strptime(value, '%Y-%m-%d %H:%M:%S')[0:6])))

o.add_option("-d", "--date", dest="date", action="callback", callback=store_date,
             type="string",
             help="Start date, in format yyyy-mm-dd HH:MM:SS", default=datetime.today())
o.add_option("-v", "--verbose", dest="verbose", default=False, action="store_true",
             help="Verbose mode (print all SQL statements)")
o.add_option("-h", "--host", dest="host", default="localhost",
             help="Database host")
o.add_option("-U", "--username", dest="user", default=os.environ.get('USER', None),
             help="Database username")

try:
    (options, (dbname, csvfile, limit)) = o.parse_args()
    limit = int(limit)
except:
    o.print_help()
    raise

password = raw_input("Password: ")

print """Starting record creation.
    csvfile:   %s
    date:   %s
    limit:  %s
    """ % (csvfile, options.date.isoformat(), limit)

# Values for randomizing our test db.
builds   =  ['042604', '042510', '042504', '042404', '042304', '042204', '042104', '042020', '042005', '042004', '041904', '041805', '041804', '041704', '041618', '041612', '041604']

appversions = (
    (1,    ("Firefox", "1.0")),
    (1,    ("Firefox", "1.0.6")),
    (2,    ("Firefox", "1.0.7")),
    (2,    ("Firefox", "1.5.0.3")),
    (2,    ("Firefox", "1.5.0.4")),
    (1,    ("Firefox", "1.5.0.5")),
    (2,    ("Firefox", "1.5.0.6")),
    (2,    ("Firefox", "1.5.0.7")),
    (4,    ("Firefox", "1.5.0.8")),
    (1,    ("Firefox", "1.5.0.9pre")),
    (8,    ("Firefox", "1.5.0.9")),
    (2,    ("Firefox", "1.5.0.10pre")),
    (14,   ("Firefox", "1.5.0.10")),
    (2,    ("Firefox", "1.5.0.11pre")),
    (895,  ("Firefox", "1.5.0.11")),
    (24,   ("Firefox", "1.5.0.12pre")),
    (18,   ("Firefox", "1.5.0.12")),
    (24,   ("Firefox", "1.5.0.13pre")),
    (2,    ("Firefox", "2.0")),
    (12,   ("Firefox", "2.0.0.1")),
    (23,   ("Firefox", "2.0.0.2")),
    (24,   ("Firefox", "2.0.0.3pre")),
    (1420, ("Firefox", "2.0.0.3")),
    (28,   ("Firefox", "2.0.0.4pre")),
    (90,   ("Firefox", "2.0.0.4")),
    (12,   ("Firefox", "2.0.0.5pre")),
    (1,    ("Firefox", "3.0a2pre")),
    (5,    ("Firefox", "3.0a2")),
    (3,    ("Firefox", "3.0a3pre")),
    (18,   ("Firefox", "3.0a3")),
    (12,   ("Firefox", "3.0a4pre")),
    (65,   ("Firefox", "3.0a4")),
    (22,   ("Firefox", "3.0a5pre")),
    (1,    ("Thunderbird", "1.0")),
    (1,    ("Thunderbird", "1.0.6")),
    (1,    ("Thunderbird", "1.0.7")),
    (1,    ("Thunderbird", "1.5.0.3")),
    (1,    ("Thunderbird", "1.5.0.4")),
    (1,    ("Thunderbird", "1.5.0.5")),
    (1,    ("Thunderbird", "1.5.0.6")),
    (3,    ("Thunderbird", "1.5.0.8")),
    (3,    ("Thunderbird", "1.5.0.9")),
    (8,    ("Thunderbird", "1.5.0.10")),
    (1,    ("Thunderbird", "1.5.0.11pre")),
    (600,  ("Thunderbird", "1.5.0.11")),
    (7,    ("Thunderbird", "1.5.0.12pre")),
    (9,    ("Thunderbird", "1.5.0.12")),
    (12,   ("Thunderbird", "1.5.0.13pre")),
    (1,    ("Thunderbird", "2.0")),
    (18,   ("Thunderbird", "2.0.0.4pre")),
    (46,   ("Thunderbird", "2.0.0.4")),
    (12,   ("Thunderbird", "2.0.0.5pre")),
    (1,    ("Thunderbird", "3.0a2pre")),
    (5,    ("Thunderbird", "3.0a2")),
    (3,    ("Thunderbird", "3.0a3pre")),
    (3,    ("Thunderbird", "3.0a3")),
    (5,    ("Thunderbird", "3.0a4pre")),
    (4,    ("Thunderbird", "3.0a4")),
    (5,    ("Thunderbird", "3.0a5pre")),
    (1,    ("SeaMonkey", "1.5.0.5")),
    (2,    ("SeaMonkey", "1.5.0.6")),
    (2,    ("SeaMonkey", "1.5.0.7")),
    (4,    ("SeaMonkey", "1.5.0.8")),
    (1,    ("SeaMonkey", "1.5.0.9pre")),
    (8,    ("SeaMonkey", "1.5.0.9")),
    (2,    ("SeaMonkey", "1.5.0.10pre")),
    (14,   ("SeaMonkey", "1.5.0.10")),
    (2,    ("SeaMonkey", "1.5.0.11pre")),
    (240,  ("SeaMonkey", "1.5.0.11")),
    (24,   ("SeaMonkey", "1.5.0.12pre")),
    (18,   ("SeaMonkey", "1.5.0.12")),
    (24,   ("SeaMonkey", "1.5.0.13pre")),
    (1,    ("SeaMonkey", "2.0a2pre")),
    (5,    ("SeaMonkey", "2.0a2")),
    (3,    ("SeaMonkey", "2.0a3pre")),
    (18,   ("SeaMonkey", "2.0a3")),
    (12,   ("SeaMonkey", "2.0a4pre")),
    (32,   ("SeaMonkey", "2.0a4")),
    (22,   ("SeaMonkey", "2.0a5pre")),
    (2,    ("Mozilla", "1.7.9")),
    (2,    ("Mozilla", "1.7.10")),
    (1,    ("Mozilla", "1.7.11")),
    (2,    ("Mozilla", "1.7.12")),
    (2,    ("Mozilla", "1.7.13")),
)

# Try to connect to db.
try:
    connection = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (dbname, options.user, options.host, password))
except:
    print 'Unable to connect to database'
    sys.exit(2)

def generate_progressive_date(start):
    while True:
        start = start + timedelta(seconds=randint(-1, 3))
        yield start

dates = generate_progressive_date(options.date)

def generate_weighted_list():
    for (weight, version) in appversions:
        for x in range(weight):
            yield version

weighted_versions = [version for version in generate_weighted_list()]

def random_uuid():
    return "%08x-%04x-%04x-%04x-%08x%04x" % (randint(0, 0xFFFFFFFF),
                                             randint(0, 0xFFFF),
                                             randint(0, 0xFFFF),
                                             randint(0, 0xFFFF),
                                             randint(0, 0xFFFFFFFF),
                                             randint(0, 0xFFFFFFFF))

def sql_sanify(value):
    return value.replace("'", "''").replace("\\", "\\\\")

# Format of the input file is (enjoy!):
#
# <product id>,<build id>,<incident id>,<crash date>,<os>,<seconds since last
# crash>,<total uptime since install>,<unique user id>,<email address>,<stack
# signature>,<source file>,<line no.>,<user submitted url>,<user submitted
# comments>

# Super loop, super dirty!  It makes me want to shower.
#
# But seriously, we can't just read it into a massive list of dicts
# because we'd run out of memory given the sheer number of iterations.

os_splitter = re.compile("^(.*) \\[(.*)\\]$")

i = 0
while True:
    for line in open(csvfile,'r'):
        print i
        line = line.strip()
        if line == '':
            continue
        
        # Pick a random app, version, build.
        (app, version) = choice(weighted_versions)
        build = "%04u%02u%02u%02u" % (randint(2006, 2007),
                                      randint(1, 12),
                                      randint(0, 30),
                                      randint(0, 23))

        # Use our test data to generate report rows for the randomly selected
        # app/version/build.
        (product, buildid, incident, crash_date, os_string, last_crash, uptime, uid, email, signature, file, line, url, comments) = line.split(',')

        (os, os_version) = os_splitter.match(os_string).groups()
        if os == '' and os_version.find('Darwin') != -1:
            os = 'Mac OS X'
        if os == '' and os_version.find('Linux') != -1:
            os = 'Linux'

        # Dict for our insert query.
        row = {'date':        dates.next().strftime('%Y-%m-%d %H:%M:%S'),
               'uuid':        random_uuid(),
               'product':     app,
               'version':     version,
               'build':       build,
               'signature':   sql_sanify(signature),
               'url':         sql_sanify(url),
               'install_age': uptime,
               'last_crash':  last_crash,
               'comments':    sql_sanify(comments),
               'os_name':     os,
               'os_version':  os_version
               }
        dbh = connection.cursor()
        dbh.execute("SELECT nextval('seq_reports_id') AS newid")
        row['newid'] = dbh.fetchone()[0]
        print "newid: %s" % row['newid']
        
        cmd = """
          INSERT INTO reports (
              id,
              date,
              uuid,
              product,
              version,
              build,
              signature,
              url,
              install_age,
              last_crash,
              comments,
              os_name,
              os_version
            ) VALUES (
              %(newid)s,
              '%(date)s',
              '%(uuid)s',
              '%(product)s',
              '%(version)s',
              '%(build)s',
              '%(signature)s',
              '%(url)s',
              %(install_age)s,
              %(last_crash)s,
              '%(comments)s',
              '%(os_name)s',
              '%(os_version)s'
            )""" % row

        if options.verbose:
            print cmd

        try:
            dbh.execute(cmd)
        except:
            print "Error executing command: %s" % cmd
            raise
        
        connection.commit()
        dbh.close()

        # Increment our count only if we've inserted something.
        i += 1
        if i > limit:
            connection.close()
            print """Test database created successfully.  Enjoy!"""
            sys.exit(0)
