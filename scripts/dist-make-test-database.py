#!/usr/bin/python
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
# If for some reason you want to show the queries, append 'debug' onto the
# command line:
#   python make-test-database.py test-crashes.csv '2007-04-27 22:00:00' 2 debug
#
# Questions or flames - morgamic on irc.mozilla.org
#
# Note:
#   There is probably a prettier way to write this, it is a DirtyHack++ so if
#   you have advice, let me know! :)

import sys
import psycopg2
import random

# Read in args.  Might want to do some better checking, but for now just do an
# existence check and die if it's not there.
try:
    file     =  sys.argv[1]
    date     =  sys.argv[2]
    limit    =  int(sys.argv[3])
except:
    print """Missing parameters.  Usage:
    python make-test-database.py test-crashes.csv '2007-04-27 22:00:00' 18000000 [debug]
    """
    sys.exit()

# Try opening the input file.  Die if you can't.
try:
    f = open(file,'r')
except:
    print "Cannot open file %s." % file
    sys.exit()

# Try to connect to db.
try:
    connection = psycopg2.connect("dbname='postgres' user='dbuser' host='localhost' password='dbpass'")
except:
    print 'Unable to connect to database'
    sys.exit()

print """Starting record creation.
    file:   %s
    date:   %s
    limit:  %s
    """ % (file, date, limit)

# Values for randomizing our test db.
builds   =  ['042604', '042510', '042504', '042404', '042304', '042204', '042104', '042020', '042005', '042004', '041904', '041805', '041804', '041704', '041618', '041612', '041604']
apps     =  ['Firefox', 'Thunderbird', 'Seamonkey', 'Flock', 'IE']
versions =  ['1.5','2.0','2.0.0.1','2.0.0.2','2.0.0.3','0.8','1.1','5.5','6.0','7.0']

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
i = 0

while i < limit:

    # Pick a random app, version, build.
    app = apps[random.randint(1,len(apps))-1]
    version = versions[random.randint(1,len(versions))-1]
    build = builds[random.randint(1,len(builds))-1]

    # Use our test data to generate report rows for the randomly selected
    # app/version/build.
    for j in range(random.randint(limit-i,limit)):

        line = f.readline().strip().split(',')

        # Dict for our insert query.
        if line[0] != '': 
            row = {'product':app,'version':version,'build':build,'date':date,'os_name':line[4],'last_crash':line[5],'install_age':line[6],'signature':line[9]}
            dbh = connection.cursor()
                
            if 'debug' in sys.argv:
                print """INSERT INTO reports (product, version, build,
                date, os_name, last_crash, install_age, signature) VALUES
                (%(product)s,%(version)s,%(build)s,%(date)s,%(os_name)s,
                %(last_crash)s,%(install_age)s,%(signature)s)""" % row

            dbh.execute(
            """INSERT INTO reports (product, version, build,
            date, os_name, last_crash, install_age, signature) VALUES
            (%(product)s,%(version)s,%(build)s,%(date)s,%(os_name)s,
            %(last_crash)s,%(install_age)s,%(signature)s)"""
            , row)
            connection.commit()
            dbh.close()

            # Increment our count only if we've inserted something.
            i += 1

connection.close()
print """Test database created successfully.  Enjoy!"""
sys.exit()
