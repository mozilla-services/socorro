#!/usr/bin/env python

# test_copy.py - unit test for COPY support
#
# Copyright (C) 2010-2011 Daniele Varrazzo  <daniele.varrazzo@gmail.com>
#
# psycopg2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# In addition, as a special exception, the copyright holders give
# permission to link this program with the OpenSSL library (or with
# modified versions of OpenSSL that use the same license as OpenSSL),
# and distribute linked combinations including the two.
#
# You must obey the GNU Lesser General Public License in all respects for
# all of the code used other than OpenSSL.
#
# psycopg2 is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

import os
import sys
import string
from testutils import unittest, decorate_all_tests, skip_if_no_iobase
from cStringIO import StringIO
from itertools import cycle, izip

import psycopg2
import psycopg2.extensions
from testconfig import dsn, green

def skip_if_green(f):
    def skip_if_green_(self):
        if green:
            return self.skipTest("copy in async mode currently not supported")
        else:
            return f(self)

    return skip_if_green_


if sys.version_info[0] < 3:
    _base = object
else:
     from io import TextIOBase as _base

class MinimalRead(_base):
    """A file wrapper exposing the minimal interface to copy from."""
    def __init__(self, f):
        self.f = f

    def read(self, size):
        return self.f.read(size)

    def readline(self):
        return self.f.readline()

class MinimalWrite(_base):
    """A file wrapper exposing the minimal interface to copy to."""
    def __init__(self, f):
        self.f = f

    def write(self, data):
        return self.f.write(data)


class CopyTests(unittest.TestCase):

    def setUp(self):
        self.conn = psycopg2.connect(dsn)
        self._create_temp_table()

    def _create_temp_table(self):
        curs = self.conn.cursor()
        curs.execute('''
            CREATE TEMPORARY TABLE tcopy (
              id serial PRIMARY KEY,
              data text
            )''')

    def tearDown(self):
        self.conn.close()

    def test_copy_from(self):
        curs = self.conn.cursor()
        try:
            self._copy_from(curs, nrecs=1024, srec=10*1024, copykw={})
        finally:
            curs.close()

    def test_copy_from_insane_size(self):
        # Trying to trigger a "would block" error
        curs = self.conn.cursor()
        try:
            self._copy_from(curs, nrecs=10*1024, srec=10*1024,
                copykw={'size': 20*1024*1024})
        finally:
            curs.close()

    def test_copy_from_cols(self):
        curs = self.conn.cursor()
        f = StringIO()
        for i in xrange(10):
            f.write("%s\n" % (i,))

        f.seek(0)
        curs.copy_from(MinimalRead(f), "tcopy", columns=['id'])

        curs.execute("select * from tcopy order by id")
        self.assertEqual([(i, None) for i in range(10)], curs.fetchall())

    def test_copy_from_cols_err(self):
        curs = self.conn.cursor()
        f = StringIO()
        for i in xrange(10):
            f.write("%s\n" % (i,))

        f.seek(0)
        def cols():
            raise ZeroDivisionError()
            yield 'id'

        self.assertRaises(ZeroDivisionError,
            curs.copy_from, MinimalRead(f), "tcopy", columns=cols())

    def test_copy_to(self):
        curs = self.conn.cursor()
        try:
            self._copy_from(curs, nrecs=1024, srec=10*1024, copykw={})
            self._copy_to(curs, srec=10*1024)
        finally:
            curs.close()

    @skip_if_no_iobase
    def test_copy_text(self):
        self.conn.set_client_encoding('latin1')
        self._create_temp_table()  # the above call closed the xn

        if sys.version_info[0] < 3:
            abin = ''.join(map(chr, range(32, 127) + range(160, 256)))
            about = abin.decode('latin1').replace('\\', '\\\\')

        else:
            abin = bytes(range(32, 127) + range(160, 256)).decode('latin1')
            about = abin.replace('\\', '\\\\')

        curs = self.conn.cursor()
        curs.execute('insert into tcopy values (%s, %s)',
            (42, abin))

        import io
        f = io.StringIO()
        curs.copy_to(f, 'tcopy', columns=('data',))
        f.seek(0)
        self.assertEqual(f.readline().rstrip(), about)

    @skip_if_no_iobase
    def test_copy_bytes(self):
        self.conn.set_client_encoding('latin1')
        self._create_temp_table()  # the above call closed the xn

        if sys.version_info[0] < 3:
            abin = ''.join(map(chr, range(32, 127) + range(160, 255)))
            about = abin.replace('\\', '\\\\')
        else:
            abin = bytes(range(32, 127) + range(160, 255)).decode('latin1')
            about = abin.replace('\\', '\\\\').encode('latin1')

        curs = self.conn.cursor()
        curs.execute('insert into tcopy values (%s, %s)',
            (42, abin))

        import io
        f = io.BytesIO()
        curs.copy_to(f, 'tcopy', columns=('data',))
        f.seek(0)
        self.assertEqual(f.readline().rstrip(), about)

    @skip_if_no_iobase
    def test_copy_expert_textiobase(self):
        self.conn.set_client_encoding('latin1')
        self._create_temp_table()  # the above call closed the xn

        if sys.version_info[0] < 3:
            abin = ''.join(map(chr, range(32, 127) + range(160, 256)))
            abin = abin.decode('latin1')
            about = abin.replace('\\', '\\\\')

        else:
            abin = bytes(range(32, 127) + range(160, 256)).decode('latin1')
            about = abin.replace('\\', '\\\\')

        import io
        f = io.StringIO()
        f.write(about)
        f.seek(0)

        curs = self.conn.cursor()
        psycopg2.extensions.register_type(
            psycopg2.extensions.UNICODE, curs)

        curs.copy_expert('COPY tcopy (data) FROM STDIN', f)
        curs.execute("select data from tcopy;")
        self.assertEqual(curs.fetchone()[0], abin)

        f = io.StringIO()
        curs.copy_expert('COPY tcopy (data) TO STDOUT', f)
        f.seek(0)
        self.assertEqual(f.readline().rstrip(), about)


    def _copy_from(self, curs, nrecs, srec, copykw):
        f = StringIO()
        for i, c in izip(xrange(nrecs), cycle(string.ascii_letters)):
            l = c * srec
            f.write("%s\t%s\n" % (i,l))

        f.seek(0)
        curs.copy_from(MinimalRead(f), "tcopy", **copykw)

        curs.execute("select count(*) from tcopy")
        self.assertEqual(nrecs, curs.fetchone()[0])

        curs.execute("select data from tcopy where id < %s order by id",
                (len(string.ascii_letters),))
        for i, (l,) in enumerate(curs):
            self.assertEqual(l, string.ascii_letters[i] * srec)

    def _copy_to(self, curs, srec):
        f = StringIO()
        curs.copy_to(MinimalWrite(f), "tcopy")

        f.seek(0)
        ntests = 0
        for line in f:
            n, s = line.split()
            if int(n) < len(string.ascii_letters):
                self.assertEqual(s, string.ascii_letters[int(n)] * srec)
                ntests += 1

        self.assertEqual(ntests, len(string.ascii_letters))

    def test_copy_expert_file_refcount(self):
        class Whatever(object):
            pass

        f = Whatever()
        curs = self.conn.cursor()
        self.assertRaises(TypeError,
            curs.copy_expert, 'COPY tcopy (data) FROM STDIN', f)

    def test_copy_no_column_limit(self):
        cols = [ "c%050d" % i for i in range(200) ]

        curs = self.conn.cursor()
        curs.execute('CREATE TEMPORARY TABLE manycols (%s)' % ',\n'.join(
            [ "%s int" % c for c in cols]))
        curs.execute("INSERT INTO manycols DEFAULT VALUES")

        f = StringIO()
        curs.copy_to(f, "manycols", columns = cols)
        f.seek(0)
        self.assertEqual(f.read().split(), ['\\N'] * len(cols))

        f.seek(0)
        curs.copy_from(f, "manycols", columns = cols)
        curs.execute("select count(*) from manycols;")
        self.assertEqual(curs.fetchone()[0], 2)


decorate_all_tests(CopyTests, skip_if_green)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
