import datetime
from crashstats.crashstats import utils
from unittest import TestCase


class TestUtils(TestCase):

    def test_unixtime(self):
        format = '%Y-%m-%d'
        value = datetime.datetime.strptime('2012-01-01', format)
        actual = utils.unixtime(value.strftime(format), millis=False,
                                format=format)
        expected = 1325376000

        self.assertEqual(actual, expected)

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
            self.assertEqual(d, expected[i])

    def test_parse_dump(self):
        dump = (
            'OS|Windows NT|6.1.7601 Service Pack 1\n'
            'CPU|x86|GenuineIntel family 15 model 4 stepping 9|2\n'
            'Crash|EXCEPTION_ACCESS_VIOLATION_READ|0x290|0\n'
            'Module|bad.exe|1.0.0.1234|debug.pdb|debugver|saddr|eaddr|1\n'
            '\n'
            '0|0|bad.dll|signature|cvs:cvs.m.org/repo:fname:rev|576|0x0\n'
            '0|1|bad.dll|signature|hg:hg.m.org/repo:fname:rev|576|0x0\n'
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
                    'crashed_thread': 1,
                    'threads': {
                        0: [
                            {'function': 'signature',
                             'short_signature': 'signature',
                             'source_line': '576',
                             'source_link': ('http://bonsai.m.org'
                                             '/cvsblame.cgi'
                                             '?file=fname&rev=rev&'
                                             'mark=576#576'),
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
                             'source_link': ('http://hg.m.org'
                                             '/repo/annotate/rev/fname#l576'),
                             'source_filename': 'fname',
                             'source_info': 'fname:576',
                             'instruction': '0x0',
                             'source': 'hg:hg.m.org/repo:fname:rev',
                             'frame_num': '1',
                             'signature': 'signature',
                             'module_name': 'bad.dll'}
                        ]
                    },
                    'address': '0x290'}

        # the default line length for assert would be too short to be useful
        self.maxDiff = None
        self.assertEqual(actual, expected)
