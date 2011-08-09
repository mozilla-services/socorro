#!/usr/bin/python

import sys
import time, datetime
import psycopg2, psycopg2.extensions, psycopg2.errorcodes

conn = psycopg2.connect("dbname=breakpad user=postgres")

cur = conn.cursor()

cur.execute("set maintenance_work_mem = '512MB'")

#cycle through all of the days covered by the backfill.

while curpart != 'done':

  print 'updating one day' % curpart

  cur.execute('SELECT backfill_one_day()');
  
  ( curpart, ) = cur.fetchone()
  
  print 'partition %s updated. vacuuming ...', % curpart;
  
  vacstring = 'VACUUM %s' %curpart
  
  cur.execute (vacstring)

print 'done'
