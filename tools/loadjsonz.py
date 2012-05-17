#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import sys
import socorro.storage.hbaseClient as hbase
import gzip

class JsonzLoader(object):
  def __init__(self,host,port):
    self.hbase_connection = hbase.HBaseConnectionForCrashReports(host,port)

  def close(self):
    self.hbase_connection.close()

  def load_from_file(self, uuid, path):
    jsonz_file = gzip.open(path, 'rb')
    json_string = jsonz_file.read()
    jsonz_file.close()
    self.hbase_connection.create_ooid_from_jsonz(uuid,json_string)

if __name__=="__main__":
  if len(sys.argv) != 3:
    print "Usage: loadjsonz.py <text file containing uuids and jsonz paths> <hbase host:port>\nText file should be uuid and file path seperated by a tab"
    sys.exit(1)
  input_file_path = sys.argv[1]
  host, port = sys.argv[2].split(':')
  loader = JsonzLoader(host,int(port))
  input_file = open(input_file_path,'rb')
  i = 0
  for line in input_file:
    uuid, path = line.strip().split('\t')
    loader.load_from_file(uuid, path)
    i += 1
    if i % 1000 == 0:
      print i,'reports loaded'
  loader.close()
  input_file.close()
  print "%s jsonz file(s) loaded" % i

