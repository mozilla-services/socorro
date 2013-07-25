import datetime
from cStringIO import StringIO
from nose.tools import eq_, ok_
from crashstats.crashstats import utils
from unittest import TestCase
from ordereddict import OrderedDict
import json


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

        expected = {'os_name': 'Windows NT',
                    'crashed_thread': 0,
                    'modules': [
                        {'debug_filename': 'debug.pdb',
                         'version': '1.0.0.1234',
                         'debug_identifier': 'debugver',
                         'filename': 'bad.exe'}
                    ],
                    'cpu_name': 'x86',
                    'cpu_version': ('GenuineIntel family '
                                    '15 model 4 stepping 9'),
                    'os_version': '6.1.7601 Service Pack 1',
                    'reason': 'EXCEPTION_ACCESS_VIOLATION_READ',
                    'threads': {
                        1: [
                            {'function': 'KiFastSystemCallRet',
                             'short_signature': 'KiFastSystemCallRet',
                             'source_line': '',
                             'source_link': '',
                             'source_filename': '',
                             'source_info': '',
                             'instruction': '0x0',
                             'source': '',
                             'frame_num': '0',
                             'signature': 'KiFastSystemCallRet',
                             'module_name': 'ntdll.dll'},
                            {'function': 'ZwClose',
                             'short_signature': 'ZwClose',
                             'source_line': '',
                             'source_link': '',
                             'source_filename': '',
                             'source_info': '',
                             'instruction': '0xb',
                             'source': '',
                             'frame_num': '1',
                             'signature': 'ZwClose',
                             'module_name': 'ntdll.dll'}
                        ],
                        0: [
                            {'function': 'signature',
                             'short_signature': 'signature',
                             'source_line': '576',
                             'source_link': ('http://bonsai.m.org/'
                                             'cvsblame.cgi?file=fname&'
                                             'rev=rev&mark=576#576'),
                             'source_filename': 'fname',
                             'source_info': 'fname:576',
                             'instruction': '0x0',
                             'source': 'cvs:cvs.m.org/repo:fname:rev',
                             'frame_num': '0',
                             'signature': 'signature',
                             'module_name': 'bad.dll'},
                            {'function': 'signature',
                             'short_signature': 'signature',
                             'source_line': '576',
                             'source_link': ('http://hg.m.org/repo/name/'
                                             'annotate/rev/fname#l576'),
                             'source_filename': 'fname',
                             'source_info': 'fname:576',
                             'instruction': '0x0',
                             'source': 'hg:hg.m.org/repo/name:fname:rev',
                             'frame_num': '1',
                             'signature': 'signature',
                             'module_name': 'bad.dll'}
                        ]
                    },
                    'address': '0x290'}

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
        input_str = '1234abcd-ef56-7890-ab12-abcdef123456'
        crash_id = utils.find_crash_id(input_str)
        eq_(crash_id, input_str)

        # A good string, with prefix
        input_str = 'bp-1234abcd-ef56-7890-ab12-abcdef123456'
        crash_id = utils.find_crash_id(input_str)
        eq_(crash_id, '1234abcd-ef56-7890-ab12-abcdef123456')

        # A bad string, one character missing
        input_str = 'bp-1234abcd-ef56-7890-ab12-abcdef12345'
        ok_(not utils.find_crash_id(input_str))

        # A bad string, one character not allowed
        input_str = 'bp-1234abcd-ef56-7890-ab12-abcdef12345g'
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
