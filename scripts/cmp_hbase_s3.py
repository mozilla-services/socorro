#!/usr/bin/env python

import os, sys
import happybase
import logging

from boto.sqs import connect_to_region as sqs_connect
from boto.sqs.jsonmessage import JSONMessage
from boto.s3 import connect_to_region as s3_connect
from boto.s3.key import Key
from boto.exception import BotoServerError

from multiprocessing import Process as TaskClass
from multiprocessing import JoinableQueue as Queue

import signal
import random

from collections import deque
import hashlib


logger = logging.getLogger(__name__)

# Following params need to be adjusted based on payload size, bandwidth etc
MAX_ROWS_IN_FLIGHT = 4096
TASK_QUEUE_SIZE = MAX_ROWS_IN_FLIGHT * 4


class HBaseSource:
  def __init__(self, addr, row_range, max_rows = 2048, batch_size = 256, stop_after_nrows = -1):
    self.thrift_addr = addr
    self.start_row, self.end_row = row_range
    self.max_rows = max_rows
    self.batch_size = batch_size
    self.stop_after_nrows = stop_after_nrows

    if (self.stop_after_nrows > 0) and (stop_after_nrows < max_rows):
      self.max_rows = self.stop_after_nrows + 1

  def items(self):
    prev_last_read_key = None
    curr_last_read_key = self.start_row
    end_row = self.end_row
    stop_after_nrows = self.stop_after_nrows
    total_read_rows = 0

    while True:
      src_tbl = happybase.Connection(random.choice(self.thrift_addr)).table('crash_reports')

      nrows = 0

      try:
        logger.debug('fetch %d rows of data via thrift', self.max_rows)

        # scan fetches rows with key in the range [row_start, row_stop)
        # this necessitates the check for repeating keys as stopping condition
        #
        logger.info("scan start")
        data = deque(src_tbl.scan(row_start = curr_last_read_key,
                                  row_stop = end_row,
                                  columns = ['raw_data', 'processed_data', 'meta_data'],
                                  limit = self.max_rows,
                                  batch_size = self.batch_size))
        logger.info("scan end %d rows starting at %s", len(data), data[0][0])
        while True:
          if not data:
            break

          key, val = data.popleft()
          if (key == prev_last_read_key):
            # last record from previous batch should be ignored
            continue

          yield key, val
          nrows += 1
          total_read_rows += 1

          if (stop_after_nrows > 0) and (stop_after_nrows == total_read_rows):
            break

          prev_last_read_key = curr_last_read_key
          curr_last_read_key = key

        logger.debug('read %d rows of data from hbase ending at %s; total %s', nrows, curr_last_read_key, total_read_rows)
        if nrows < self.max_rows:
          print >> sys.stderr, "end of range. exiting"
          break

      except happybase.hbase.ttypes.IOError:
        logger.exception('caught exception. retrying.')

      except Exception:
        logger.exception('unrecoverable exception.')
        raise

class SourceWorker(TaskClass):
  def __init__(self, queue, source_config):
    TaskClass.__init__(self)

    self.source = HBaseSource(*source_config)
    self.queue = queue

  def run(self):
    num_rows_written = 0
    total_size_written = 0
    s3_path_tmpl = 'v1/{ftype}/{uuid}'
    env = 'stage'

    for key, cols in self.source.items():
      dump_names = []
      for j in cols.keys():

        suffix = get_suffix(j)
        if not suffix:
          #logger.info('column %s ignored for key %s', j, key)
          continue

        if j.startswith('raw_data'):
          dump_names.append(suffix)

        # crashstats/stage/v1/
        # format  {{bucket}}/{{prefix}}/{{version}}/{{crash_type}}/{{crash_id}}
        skey = s3_path_tmpl.format(env = env,
                                   uuid = key[7:],
                                   ftype = suffix)

        self.queue.put((skey, cols[j]))

        total_size_written += len(cols[j])

      num_rows_written += 1

      if ((num_rows_written % 1000) == 0):
        logger.info("wrote %d rows, at %s", num_rows_written, key)
        logger.warn("qsize is %d", self.queue.qsize())

    print >> sys.stderr, "SourceWorker DONE", num_rows_written, total_size_written

class S3Worker(TaskClass):
  def __init__(self, s3_region, s3_bucket, task_queue, result_queue):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    TaskClass.__init__(self)
    self.task_queue = task_queue
    self.result_queue = result_queue
    self.s3_region = s3_region
    self.s3_bucket = s3_bucket
    self.num_rows = 0

  def setup_s3(self):
    self.s3 = s3_connect(self.s3_region)
    self.bucket = self.s3.get_bucket(self.s3_bucket)

  def cmp_s3_hash(self, key, val):
    k = self.bucket.get_key(key)
    s3_md5 = k.etag[1:-1]
    hbase_md5 = hashlib.md5(val).hexdigest()
    self.num_rows += 1

    if s3_md5 != hbase_md5:
      print >> sys.stderr, "MISMATCH", k, key, s3_md5, hbase_md5

  def run(self):
    self.setup_s3()

    while True:
      kv = self.task_queue.get()

      if kv is None:
        print >> sys.stderr, '%s: Exiting' % self.name
        self.task_queue.task_done()
        break

      k, v = kv

      while True:
        try:
          self.cmp_s3_hash(k, v)
          break
        except BotoServerError:
          pass

      self.task_queue.task_done()
    return

def get_suffix(colname):
  suffix_map = {
    'processed_data:json' : 'processed_crash',
    'raw_data:dump' : 'dump',
    'meta_data:json' : 'raw_crash',
    'raw_data:upload_file_minidump_browser' : 'upload_file_minidump_browser',
    'raw_data:upload_file_minidump_flash1' : 'upload_file_minidump_flash1',
    'raw_data:upload_file_minidump_flash2' : 'upload_file_minidump_flash2'
    }

  if colname in suffix_map:
    return suffix_map[colname]
  elif colname.startswith('raw_data'):
    return colname.split(':', 1)[1]
  else:
    return None


def main(num_workers = 64):
  if len(sys.argv) != 3:
    show_usage_and_quit()

  queue = Queue(TASK_QUEUE_SIZE)

  # start s3 workers
  workers = [S3Worker('us-west-2', 'org.mozilla.crash-stats.production.crashes', queue, None)
             for i in xrange(num_workers)]

  for i in workers:
    i.start()

  thrift_hosts = sys.argv[1].split(',')
  date = sys.argv[2]

  # start hbase workers
  key_ranges = []
  for i in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']:
    key_ranges.append(('%s%s%s' % (i, date, i), '%s%s%sg' % (i, date, i)))

  num_hbase_workers = 1

  for i in xrange(0, len(key_ranges), num_hbase_workers):
    src_workers = []
    krng = key_ranges[i : (i + num_hbase_workers)]

    for j in range(len(krng)):
      src_workers.append(SourceWorker(queue, (thrift_hosts, krng[j], 2048, 256, 10241)))

    for w in src_workers:
      print "starting src worker", w
      w.start()

    for w in src_workers:
      w.join()

  for i in workers:
    queue.put(None)

  queue.join()

def show_usage_and_quit():
  print >> sys.stderr, "Usage: %s hosts('host1,host2,host3') date(YYMMDD)" % (sys.argv[0])
  sys.exit(2)


if __name__ == '__main__':
    logging.basicConfig(format = '%(asctime)s %(name)s:%(levelname)s: %(message)s',
                        level = logging.INFO)

    main()
