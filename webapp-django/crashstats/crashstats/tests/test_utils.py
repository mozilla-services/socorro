import datetime
from cStringIO import StringIO
from unittest import TestCase
from ordereddict import OrderedDict
import json

from nose.tools import eq_, ok_

from django.http import HttpResponse
from django.test.client import RequestFactory

from crashstats.crashstats import utils


class TestUtils(TestCase):

    def test_unixtime(self):
        format = '%Y-%m-%d'
        value = datetime.datetime.strptime('2012-01-01', format)
        actual = utils.unixtime(value.strftime(format), millis=False,
                                format=format)
        expected = 1325376000

        eq_(actual, expected)

    def test_daterange(self):
        format = '%Y-%m-%d'
        start_date = datetime.datetime.strptime('2012-01-01', format)
        end_date = datetime.datetime.strptime('2012-01-05', format)

        expected = [
            '2012-01-01',
            '2012-01-02',
            '2012-01-03',
            '2012-01-04'
        ]

        for i, d in enumerate(utils.daterange(start_date, end_date, format)):
            eq_(d, expected[i])

    def test_enhance_frame(self):
        vcs_mappings = {
            'hg': {
                'hg.m.org': ('http://hg.m.org/'
                             '%(repo)s/annotate/%(revision)s'
                             '/%(file)s#l%(line)s')
            }
        }

        # Test with a file that uses a vcs_mapping.
        # Also test function sanitizing.
        actual = {
            'frame': 0,
            'module': 'bad.dll',
            'function': 'Func(A * a,B b)',
            'file': 'hg:hg.m.org/repo/name:dname/fname:rev',
            'line': 576,
        }
        utils.enhance_frame(actual, vcs_mappings)
        expected = {
            'function': 'Func(A* a, B b)',
            'short_signature': 'Func',
            'line': 576,
            'source_link': ('http://hg.m.org/repo/name/'
                            'annotate/rev/dname/fname#l576'),
            'file': 'dname/fname',
            'frame': 0,
            'signature': 'Func(A* a, B b)',
            'module': 'bad.dll',
        }
        eq_(actual, expected)

        # Now with a file that has VCS info but isn't in vcs_mappings.
        actual = {
            'frame': 0,
            'module': 'bad.dll',
            'function': 'Func',
            'file': 'git:git.m.org/repo/name:dname/fname:rev',
            'line': 576,
        }
        utils.enhance_frame(actual, vcs_mappings)
        expected = {
            'function': 'Func',
            'short_signature': 'Func',
            'line': 576,
            'file': 'fname',
            'frame': 0,
            'signature': 'Func',
            'module': 'bad.dll',
        }
        eq_(actual, expected)

        # Test with no VCS info at all.
        actual = {
            'frame': 0,
            'module': 'bad.dll',
            'function': 'Func',
            'file': '/foo/bar/file.c',
            'line': 576,
        }
        utils.enhance_frame(actual, vcs_mappings)
        expected = {
            'function': 'Func',
            'short_signature': 'Func',
            'line': 576,
            'file': '/foo/bar/file.c',
            'frame': 0,
            'signature': 'Func',
            'module': 'bad.dll',
        }
        eq_(actual, expected)

        # Test with no source info at all.
        actual = {
            'frame': 0,
            'module': 'bad.dll',
            'function': 'Func',
        }
        utils.enhance_frame(actual, vcs_mappings)
        expected = {
            'function': 'Func',
            'short_signature': 'Func',
            'frame': 0,
            'signature': 'Func',
            'module': 'bad.dll',
        }
        eq_(actual, expected)

        # Test with no function info.
        actual = {
            'frame': 0,
            'module': 'bad.dll',
            'module_offset': '0x123',
        }
        utils.enhance_frame(actual, vcs_mappings)
        expected = {
            'short_signature': 'bad.dll@0x123',
            'frame': 0,
            'signature': 'bad.dll@0x123',
            'module': 'bad.dll',
            'module_offset': '0x123',
        }
        eq_(actual, expected)

        # Test with no module info.
        actual = {
            'frame': 0,
            'offset': '0x1234',
        }
        utils.enhance_frame(actual, vcs_mappings)
        expected = {
            'short_signature': '@0x1234',
            'frame': 0,
            'signature': '@0x1234',
            'offset': '0x1234',
        }
        eq_(actual, expected)

    def test_enhance_json_dump(self):
        vcs_mappings = {
            'hg': {
                'hg.m.org': ('http://hg.m.org/'
                             '%(repo)s/annotate/%(revision)s'
                             '/%(file)s#l%(line)s')
            }
        }

        actual = {'threads':
                  [{'frames':
                    [
                        {'frame': 0,
                         'module': 'bad.dll',
                         'function': 'Func',
                         'file': 'hg:hg.m.org/repo/name:dname/fname:rev',
                         'line': 576},
                        {'frame': 1,
                         'module': 'another.dll',
                         'function': 'Func2',
                         'file': 'hg:hg.m.org/repo/name:dname/fname:rev',
                         'line': 576}
                    ]},
                   {'frames':
                    [
                        {'frame': 0,
                         'module': 'bad.dll',
                         'function': 'Func',
                         'file': 'hg:hg.m.org/repo/name:dname/fname:rev',
                         'line': 576},
                        {'frame': 1,
                         'module': 'another.dll',
                         'function': 'Func2',
                         'file': 'hg:hg.m.org/repo/name:dname/fname:rev',
                         'line': 576}
                    ]}]}
        utils.enhance_json_dump(actual, vcs_mappings)
        expected = {'threads':
                    [{'thread': 0,
                      'frames':
                      [{'frame': 0,
                        'function': 'Func',
                        'short_signature': 'Func',
                        'line': 576,
                        'source_link': ('http://hg.m.org/repo/name/'
                                        'annotate/rev/dname/fname#l576'),
                        'file': 'dname/fname',
                        'signature': 'Func',
                        'module': 'bad.dll'},
                       {'frame': 1,
                        'module': 'another.dll',
                        'function': 'Func2',
                        'signature': 'Func2',
                        'short_signature': 'Func2',
                        'source_link': ('http://hg.m.org/repo/name/'
                                        'annotate/rev/dname/fname#l576'),
                        'file': 'dname/fname',
                        'line': 576}]},
                     {'thread': 1,
                      'frames':
                      [{'frame': 0,
                        'function': 'Func',
                        'short_signature': 'Func',
                        'line': 576,
                        'source_link': ('http://hg.m.org/repo/name/'
                                        'annotate/rev/dname/fname#l576'),
                        'file': 'dname/fname',
                        'signature': 'Func',
                        'module': 'bad.dll'},
                       {'frame': 1,
                        'module': 'another.dll',
                        'function': 'Func2',
                        'signature': 'Func2',
                        'short_signature': 'Func2',
                        'source_link': ('http://hg.m.org/repo/name/'
                                        'annotate/rev/dname/fname#l576'),
                        'file': 'dname/fname',
                        'line': 576}]}]}
        eq_(actual, expected)

    def test_parse_dump(self):
        dump = (
            'OS|Windows NT|6.1.7601 Service Pack 1\n'
            'CPU|x86|GenuineIntel family 15 model 4 stepping 9|2\n'
            'Crash|EXCEPTION_ACCESS_VIOLATION_READ|0x290|0\n'
            'Module|bad.exe|1.0.0.1234|debug.pdb|debugver|saddr|eaddr|1\n'
            '\n'
            '0|0|bad.dll|signature|cvs:cvs.m.org/repo:fname:rev|576|0x0\n'
            '0|1|bad.dll|signature|hg:hg.m.org/repo/name:fname:rev|576|0x0\n'
            '1|0|ntdll.dll|KiFastSystemCallRet|||0x0\n'
            '1|1|ntdll.dll|ZwClose|||0xb\n'
            '1|2|ntdll.dll||||0xabc\n'
            '1|3|||||0x1234\n'
        )

        vcs_mappings = {
            'cvs': {
                'cvs.m.org': ('http://bonsai.m.org/cvsblame.cgi?'
                              'file=%(file)s&rev=%(revision)s&'
                              'mark=%(line)s#%(line)s')
            },
            'hg': {
                'hg.m.org': ('http://hg.m.org/'
                             '%(repo)s/annotate/%(revision)s'
                             '/%(file)s#l%(line)s')
            }
        }

        actual = utils.parse_dump(dump, vcs_mappings)

        expected = {
            'status': 'OK',
            'system_info': {
                'os': 'Windows NT',
                'os_ver': '6.1.7601 Service Pack 1',
                'cpu_arch': 'x86',
                'cpu_info': 'GenuineIntel family 15 model 4 stepping 9',
                'cpu_count': 2},
            'crash_info': {
                'crashing_thread': 0,
                'crash_address': '0x290',
                'type': 'EXCEPTION_ACCESS_VIOLATION_READ'},
            'main_module': 0,
            'modules': [
                {'debug_file': 'debug.pdb',
                 'version': '1.0.0.1234',
                 'debug_id': 'debugver',
                 'filename': 'bad.exe',
                 'base_addr': 'saddr',
                 'end_addr': 'eaddr'}],
            'thread_count': 2,
            'threads': [
                {'thread': 0,
                 'frame_count': 2,
                 'frames': [
                     {'function': 'signature',
                      'short_signature': 'signature',
                      'line': 576,
                      'source_link': ('http://bonsai.m.org/'
                                      'cvsblame.cgi?file=fname&'
                                      'rev=rev&mark=576#576'),
                      'file': 'fname',
                      'frame': 0,
                      'signature': 'signature',
                      'module': 'bad.dll'},
                     {'function': 'signature',
                      'short_signature': 'signature',
                      'line': 576,
                      'source_link': ('http://hg.m.org/repo/name/'
                                      'annotate/rev/fname#l576'),
                      'file': 'fname',
                      'frame': 1,
                      'signature': 'signature',
                      'module': 'bad.dll'}
                 ]},
                {'thread': 1,
                 'frame_count': 4,
                 'frames': [
                     {'function': 'KiFastSystemCallRet',
                      'short_signature': 'KiFastSystemCallRet',
                      'function_offset': '0x0',
                      'frame': 0,
                      'signature': 'KiFastSystemCallRet',
                      'module': 'ntdll.dll'},
                     {'function': 'ZwClose',
                      'short_signature': 'ZwClose',
                      'function_offset': '0xb',
                      'frame': 1,
                      'signature': 'ZwClose',
                      'module': 'ntdll.dll'},
                     {'signature': 'ntdll.dll@0xabc',
                      'short_signature': 'ntdll.dll@0xabc',
                      'module_offset': '0xabc',
                      'frame': 2,
                      'module': 'ntdll.dll'},
                     {'offset': '0x1234',
                      'frame': 3,
                      'signature': '@0x1234',
                      'short_signature': '@0x1234'}]}]
        }

        # the default line length for assert would be too short to be useful
        self.maxDiff = None
        eq_(actual, expected)

    def test_parse_dump_invalid_frames(self):
        """What's special about this one is that the dump is bad in that
        it starts wiht a 2 but there's no 0 or 1.
        So what the parse_dump() function does is that it pads everything
        to the left with blocks of empty frames.

        See https://bugzilla.mozilla.org/show_bug.cgi?id=1071043
        """

        dump = (
            'OS|Windows NT|6.1.7601 Service Pack 1\n'
            'CPU|x86|GenuineIntel family 15 model 4 stepping 9|2\n'
            'Crash|EXCEPTION_ACCESS_VIOLATION_READ|0x290|0\n'
            'Module|bad.exe|1.0.0.1234|debug.pdb|debugver|saddr|eaddr|1\n'
            '\n'
            '2|0|bad.dll|signature|cvs:cvs.m.org/repo:fname:rev|576|0x0\n'
        )

        vcs_mappings = {
            'cvs': {
                'cvs.m.org': ('http://bonsai.m.org/cvsblame.cgi?'
                              'file=%(file)s&rev=%(revision)s&'
                              'mark=%(line)s#%(line)s')
            },
            'hg': {
                'hg.m.org': ('http://hg.m.org/'
                             '%(repo)s/annotate/%(revision)s'
                             '/%(file)s#l%(line)s')
            }
        }

        actual = utils.parse_dump(dump, vcs_mappings)

        expected = {
            'crash_info': {
                'crash_address': '0x290',
                'crashing_thread': 0,
                'type': 'EXCEPTION_ACCESS_VIOLATION_READ'
            },
            'main_module': 0,
            'modules': [{
                'base_addr': 'saddr',
                'debug_file': 'debug.pdb',
                'debug_id': 'debugver',
                'end_addr': 'eaddr',
                'filename': 'bad.exe',
                'version': '1.0.0.1234'
            }],
            'status': 'OK',
            'system_info': {
                'cpu_arch': 'x86',
                'cpu_count': 2,
                'cpu_info': 'GenuineIntel family 15 model 4 stepping 9',
                'os': 'Windows NT',
                'os_ver': '6.1.7601 Service Pack 1'
            },
            'thread_count': 3,
            'threads': [
                {
                    'frame_count': 0,
                    'frames': [],
                    'thread': 0
                },
                {
                    'frame_count': 0,
                    'frames': [],
                    'thread': 1
                },
                {
                    'frame_count': 1,
                    'frames': [{
                        'file': 'fname',
                        'frame': 0,
                        'function': 'signature',
                        'line': 576,
                        'module': 'bad.dll',
                        'short_signature': 'signature',
                        'signature': 'signature',
                        'source_link': (
                            'http://bonsai.m.org/cvsblame.cgi?file=fname&'
                            'rev=rev&mark=576#576'
                        )
                    }],
                    'thread': 2
                },
            ]
        }

        # the default line length for assert would be too short to be useful
        self.maxDiff = None
        eq_(actual, expected)

    def test_build_releases(self):
        now = datetime.datetime.utcnow()
        now = now.replace(microsecond=0).isoformat()

        currentversions = json.loads("""
            {"currentversions": [
             {"product": "WaterWolf",
              "throttle": "100.00",
              "end_date": "%(end_date)s",
              "start_date": "2012-03-08T00:00:00",
              "featured": true,
              "version": "19.0",
              "release": "Beta",
              "id": 922},
             {"product": "WaterWolf",
              "throttle": "100.00",
              "end_date": "%(end_date)s",
              "start_date": "2012-03-08T00:00:00",
              "featured": true,
              "version": "18.0",
              "release": "Stable",
              "id": 920},
             {"product": "WaterWolf",
              "throttle": "100.00",
              "end_date": "%(end_date)s",
              "start_date": "2012-03-08T00:00:00",
              "featured": true,
              "version": "20.0",
              "release": "Nightly",
              "id": 923},
              {"product": "NightTrain",
              "throttle": "100.00",
              "end_date": "%(end_date)s",
              "start_date": "2012-03-08T00:00:00",
              "featured": true,
              "version": "18.0",
              "release": "Aurora",
              "id": 924},
             {"product": "NightTrain",
              "throttle": "100.00",
              "end_date": "%(end_date)s",
              "start_date": "2012-03-08T00:00:00",
              "featured": true,
              "version": "19.0",
              "release": "Nightly",
              "id": 925},
             {"product": "SeaMonkey",
              "throttle": "99.00",
              "end_date": "2012-05-10T00:00:00",
              "start_date": "2012-03-08T00:00:00",
              "featured": true,
              "version": "9.5",
              "release": "Alpha",
              "id": 921}]
              }
              """ % {'end_date': now})['currentversions']

        actual = utils.build_releases(currentversions)

        expected = OrderedDict([
            (u'WaterWolf', [
             {u'throttle': u'100.00',
              u'end_date': now,
              u'start_date': u'2012-03-08T00:00:00',
              u'featured': True,
              u'version': u'19.0',
              u'release': u'Beta',
              u'id': 922},
             {u'throttle': u'100.00',
              u'end_date': now,
              u'start_date': u'2012-03-08T00:00:00',
              u'featured': True,
              u'version': u'18.0',
              u'release': u'Stable',
              u'id': 920},
             {u'throttle': u'100.00',
              u'end_date': now,
              u'start_date': u'2012-03-08T00:00:00',
              u'featured': True,
              u'version': u'20.0',
              u'release': u'Nightly',
              u'id': 923}
             ]),
            (u'NightTrain', [
             {u'throttle': u'100.00',
              u'end_date': now,
              u'start_date': u'2012-03-08T00:00:00',
              u'featured': True,
              u'version': u'18.0',
              u'release': u'Aurora',
              u'id': 924},
             {u'throttle': u'100.00',
              u'end_date': now,
              u'start_date': u'2012-03-08T00:00:00',
              u'featured': True,
              u'version': u'19.0',
              u'release': u'Nightly',
              u'id': 925}
             ])
        ])
        eq_(actual, expected)

    def test_find_crash_id(self):
        # A good string, no prefix
        input_str = '1234abcd-ef56-7890-ab12-abcdef130802'
        crash_id = utils.find_crash_id(input_str)
        eq_(crash_id, input_str)

        # A good string, with prefix
        input_str = 'bp-1234abcd-ef56-7890-ab12-abcdef130802'
        crash_id = utils.find_crash_id(input_str)
        eq_(crash_id, '1234abcd-ef56-7890-ab12-abcdef130802')

        # A good looking string but not a real day
        input_str = '1234abcd-ef56-7890-ab12-abcdef130230'  # Feb 30th 2013
        ok_(not utils.find_crash_id(input_str))
        input_str = 'bp-1234abcd-ef56-7890-ab12-abcdef130230'
        ok_(not utils.find_crash_id(input_str))

        # A bad string, one character missing
        input_str = 'bp-1234abcd-ef56-7890-ab12-abcdef12345'
        ok_(not utils.find_crash_id(input_str))

        # A bad string, one character not allowed
        input_str = 'bp-1234abcd-ef56-7890-ab12-abcdef12345g'
        ok_(not utils.find_crash_id(input_str))

        # Close but doesn't end with 6 digits
        input_str = 'f48e9617-652a-11dd-a35a-001a4bd43ed6'
        ok_(not utils.find_crash_id(input_str))

        # A random string that does not match
        input_str = 'somerandomstringthatdoesnotmatch'
        ok_(not utils.find_crash_id(input_str))

    def test_unicode_writer(self):
        out = StringIO()
        writer = utils.UnicodeWriter(out)
        writer.writerow([
            'abc',
            u'\xe4\xc3',
            123,
            1.23,
        ])

        result = out.getvalue()
        ok_(isinstance(result, str))
        u_result = unicode(result, 'utf-8')
        ok_('abc,' in u_result)
        ok_(u'\xe4\xc3,' in u_result)
        ok_('123,' in u_result)
        ok_('1.23' in u_result)

    def test_json_view_basic(self):
        request = RequestFactory().get('/')

        def func(request):
            return {'one': 'One'}

        func = utils.json_view(func)
        response = func(request)
        ok_(isinstance(response, HttpResponse))
        eq_(json.loads(response.content), {'one': 'One'})
        eq_(response.status_code, 200)

    def test_json_view_indented(self):
        request = RequestFactory().get('/?pretty=print')

        def func(request):
            return {'one': 'One'}

        func = utils.json_view(func)
        response = func(request)
        ok_(isinstance(response, HttpResponse))
        eq_(json.dumps({'one': 'One'}, indent=2), response.content)
        eq_(response.status_code, 200)

    def test_json_view_already_httpresponse(self):
        request = RequestFactory().get('/')

        def func(request):
            return HttpResponse('something')

        func = utils.json_view(func)
        response = func(request)
        ok_(isinstance(response, HttpResponse))
        eq_(response.content, 'something')
        eq_(response.status_code, 200)

    def test_json_view_custom_status(self):
        request = RequestFactory().get('/')

        def func(request):
            return {'one': 'One'}, 403

        func = utils.json_view(func)
        response = func(request)
        ok_(isinstance(response, HttpResponse))
        eq_(json.loads(response.content), {'one': 'One'})
        eq_(response.status_code, 403)
