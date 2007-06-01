#!/usr/bin/python

"""Submit minidumps to a collector at a specified rate for load-testing
and collector synchronicity testing purposes."""

import urllib2_file
import urllib2
import simplejson
from optparse import OptionParser
from time import sleep, time

op = OptionParser(usage='usage: python collector-loadtesting.py [options] file.json+')
op.add_option('-u', '--url',
              dest='url', default='http://localhost/crash-reports/submit',
              help="Submission URL: default http://localhost/crash-reports/submit")
op.add_option('-l', '--load',
              dest="load", type="int", default=60000,
              help="Submissions-per-day to test, default 60000")

(options, files) = op.parse_args()

SECONDS_PER_DAY = 60. * 60 * 24
seconds_per_report = SECONDS_PER_DAY /  options.load

print "Sending every %f seconds" % seconds_per_report

def getFile():
  last_time = 0
  while True:
    for jsonfile in files:
      t = time()
      if t < last_time + seconds_per_report:
        w = t - last_time + seconds_per_report
        print "Sleeping %s seconds" % w
        sleep(w)
      last_time = t
      yield jsonfile

for jsonFile in getFile():
  dumpFile = jsonFile.replace('json', 'dump')
  d = simplejson.load(open(jsonFile, 'r'))
  del d['timestamp']
  d['upload_file_minidump'] = open(dumpFile, 'r')

  urllib2.urlopen(options.url, d)
