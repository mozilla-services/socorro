#!/usr/bin/env python
"""
This takes the output of PostgreSQL's JSON crashes as stdin
and stores them as a tar file that correlations reports expect.
"""

import gzip
import sys
import tarfile
import cStringIO

def main():
    if len(sys.argv) != 2:
        print 'syntax: ./tar_crashes.py <filename>'
        sys.exit(1)

    output_file = sys.argv[1]

    tar = tarfile.open('%s' % output_file, 'a')
    for line in sys.stdin:
        crash_id, processed_crash = line.split('\x02')
        compressed_crash = cStringIO.StringIO()
        gzip_file = gzip.GzipFile(fileobj=compressed_crash, mode='w')
        gzip_file.write(processed_crash)
        gzip_file.close()
        compressed_crash.seek(0)
        tarinfo = tarfile.TarInfo('%s.jsonz' % crash_id)
        tarinfo.size = len(compressed_crash.getvalue())
        tar.addfile(tarinfo, compressed_crash)
    tar.close()

if __name__ == '__main__':
    main()