#!/usr/bin/python

class BaseTable(object):
    # this should be overridden when fake data is to be generated.
    # it will work for static data as-is.
    def generate_inserts(self):
        for row in self.rows:
            yield 'INSERT INTO %s (%s) VALUES (%s)' % (self.table,
              ', '.join(self.columns), ', '.join(row))

class DailyCrashCodes(BaseTable):
    table = 'daily_crash_codes'
    columns = ['crash_code', 'crash_type']
    rows = [['C', 'CRASH_BROWSER'],
             ['P', 'OOP_PLUGIN'],
             ['H', 'HANGS_NORMALIZED'],
             ['c', 'HANG_BROWSER'],
             ['p', 'HANG_PLUGIN'],
             ['T', 'CONTENT']]

class OSNames(BaseTable):
    table = 'os_names'
    columns = ['os_name', 'os_short_name']
    rows = [['Windows', 'win'],
            ['Mac OS X' ,'mac'],
            ['Linux', 'lin']]

class OSNameMatches(BaseTable):
    table = 'os_name_matches'
    columns = ['os_name', 'match_string']
    rows = [['Windows', 'Windows%'],
            ['Mac OS X', 'Mac%'],
            ['Linux', 'Linux%']]

class ProcessTypes(BaseTable):
    table = 'process_types'
    columns = ['process_type']
    rows = [['browser'],
            ['plugin'],
            ['content']]

class Products(BaseTable):
    table = 'products'
    columns = ['product_name', 'sort', 'rapid_release_version', 'release_name']
    rows = [['WaterWolf','1','1.0','waterwolf']]

class ReleaseChannels(BaseTable):
    table = 'release_channels'
    columns = ['release_channel', 'sort']
    rows = [['Nightly', '1'],
            ['Aurora', '2'],
            ['Beta', '3'],
            ['Release', '4'],
            ['ESR', '5']]

class ProductReleaseChannels(BaseTable):
    table = 'product_release_channels'
    columns = ['product_name', 'release_channel', 'throttle']
    rows = [['WaterWolf', 'Nightly', '1.0'],
            ['WaterWolf', 'Aurora', '1.0'],
            ['WaterWolf', 'Beta', '1.0'],
            ['WaterWolf', 'Release', '1.0'],
            ['WaterWolf', 'ESR', '1.0']]

class RawADU(BaseTable):
    table = 'raw_adu'
    columns = ['adu_count', 'date', 'product_name', 'product_os_platform',
               'product_os_version', 'product_version', 'build',
               'build_channel', 'product_guid']
    # TODO generate fake data
    rows = [['17', '2012-06-15 00:00:00', 'WaterWolf', 'Linux', '', '1.0',
             '20120615000001', 'release', '{waterwolf@example.org}']]
'''
17,2012-06-15 00:00:00,WaterWolf,Linux,,1.0,20120615000001,release,{waterwolf@example.org}
8,2012-06-15 00:00:00,WaterWolf,Mac OS/X,,1.0,20120615000001,release,{waterwolf@example.org}
22,2012-06-15 00:00:00,WaterWolf,Other,,1.0,20120615000001,release,{waterwolf@example.org}
98,2012-06-15 00:00:00,WaterWolf,Windows,,1.0,20120615000001,release,{waterwolf@example.org}
10,2012-06-15 00:00:00,WaterWolf,Linux,,2.0,20120615000002,beta,{waterwolf@example.org}
9,2012-06-15 00:00:00,WaterWolf,Mac OS/X,,2.0,20120615000002,beta,{waterwolf@example.org}
12,2012-06-15 00:00:00,WaterWolf,Other,,2.0,20120615000002,beta,{waterwolf@example.org}
38,2012-06-15 00:00:00,WaterWolf,Windows,,2.0,20120615000002,beta,{waterwolf@example.org}
9,2012-06-15 00:00:00,WaterWolf,Linux,,3.0a2,20120615000002,nightly,{waterwolf@example.org}
10,2012-06-15 00:00:00,WaterWolf,Mac OS/X,,3.0a2,20120615000003,nightly,{waterwolf@example.org}
14,2012-06-15 00:00:00,WaterWolf,Other,,3.0a2,20120615000003,nightly,{waterwolf@example.org}
28,2012-06-15 00:00:00,WaterWolf,Windows,,3.0a2,20120615000003,nightly,{waterwolf@example.org}
3,2012-06-15 00:00:00,WaterWolf,Linux,,4.0a1,20120615000004,nightly,{waterwolf@example.org}
2,2012-06-15 00:00:00,WaterWolf,Mac OS/X,,4.0a1,20120615000004,nightly,{waterwolf@example.org}
48,2012-06-15 00:00:00,WaterWolf,Other,,4.0a1,20120615000004,nightly,{waterwolf@example.org}
4,2012-06-15 00:00:00,WaterWolf,Windows,,4.0a1,20120615000004,nightly,{waterwolf@example.org}
7,2012-06-16 00:00:00,WaterWolf,Linux,,1.0,20120615000001,release,{waterwolf@example.org}
18,2012-06-16 00:00:00,WaterWolf,Mac OS/X,,1.0,20120615000001,release,{waterwolf@example.org}
2,2012-06-16 00:00:00,WaterWolf,Other,,1.0,20120615000001,release,{waterwolf@example.org}
8,2012-06-16 00:00:00,WaterWolf,Windows,,1.0,20120615000001,release,{waterwolf@example.org}
1,2012-06-16 00:00:00,WaterWolf,Linux,,2.0,20120615000002,beta,{waterwolf@example.org}
19,2012-06-16 00:00:00,WaterWolf,Mac OS/X,,2.0,20120615000002,beta,{waterwolf@example.org}
2,2012-06-16 00:00:00,WaterWolf,Other,,2.0,20120615000002,beta,{waterwolf@example.org}
8,2012-06-16 00:00:00,WaterWolf,Windows,,2.0,20120615000002,beta,{waterwolf@example.org}
19,2012-06-16 00:00:00,WaterWolf,Linux,,3.0a2,20120615000003,nightly,{waterwolf@example.org}
1,2012-06-16 00:00:00,WaterWolf,Mac OS/X,,3.0a2,20120615000003,nightly,{waterwolf@example.org}
4,2012-06-16 00:00:00,WaterWolf,Other,,3.0a2,20120615000003,nightly,{waterwolf@example.org}
8,2012-06-16 00:00:00,WaterWolf,Windows,,3.0a2,20120615000003,nightly,{waterwolf@example.org}
13,2012-06-16 00:00:00,WaterWolf,Linux,,4.0a1,20120615000004,nightly,{waterwolf@example.org}
12,2012-06-16 00:00:00,WaterWolf,Mac OS/X,,4.0a1,20120615000004,nightly,{waterwolf@example.org}
8,2012-06-16 00:00:00,WaterWolf,Other,,4.0a1,20120615000004,nightly,{waterwolf@example.org}
14,2012-06-16 00:00:00,WaterWolf,Windows,,4.0a1,20120615000004,nightly,{waterwolf@example.org}
'''

class ReleaseChannelMatches(BaseTable):
    table = 'release_channel_matches'
    columns = ['release_channel', 'match_string']
    rows = [['Release','release'],
            ['Release', 'default'],
            ['Beta', 'beta'],
            ['Aurora', 'aurora'],
            ['Nightly', 'nightly%']]

class ReleasesRaw(BaseTable):
    table = 'releases_raw'
    columns = ['product_name', 'version', 'platform', 'build_id',
               'build_type', 'beta_number', 'repository']
    # TODO generate fake data
    rows = [['waterwolf', '1.0', 'linux', '20120615000001', 'Release', '',
             'mozilla-release']]
'''    
waterwolf,1.0,linux,20120615000001,Release,,mozilla-release
waterwolf,1.0,macosx,20120615000001,Release,,mozilla-release
waterwolf,1.0,win32,20120615000001,Release,,mozilla-release
waterwolf,2.0,linux,20120615000002,Beta,1,mozilla-beta
waterwolf,2.0,macosx,20120615000002,Beta,1,mozilla-beta
waterwolf,2.0,win32,20120615000002,Beta,1,mozilla-beta
waterwolf,3.0a2,linux,20120615000003,Aurora,,mozilla-aurora
waterwolf,3.0a2,macosx,20120615000003,Aurora,,mozilla-aurora
waterwolf,3.0a2,win32,20120615000003,Aurora,,mozilla-aurora
waterwolf,4.0a1,linux,20120615000004,Nightly,,mozilla-central
waterwolf,4.0a1,macosx,20120615000004,Nightly,,mozilla-central
waterwolf,4.0a1,win32,20120615000004,Nightly,,mozilla-central
'''

class UptimeLevels(BaseTable):
    table = 'uptime_levels'
    columns = ['uptime_level', 'uptime_string', 'min_uptime', 'max_uptime']
    rows = [['1', '< 1 min', '00:00:00', '00:01:00'],
            ['2', '1-5 min', '00:01:00', '00:05:00'],
            ['3', '5-15 min', '00:05:00', '00:15:00'],
            ['4', '15-60 min', '00:15:00', '01:00:00'],
            ['5', '> 1 hour', '01:00:00', '1 year']]

class WindowsVersions(BaseTable):
    table = 'windows_versions'
    columns = ['windows_version_name', 'major_version', 'minor_version']
    rows = [['Windows NT', '3', '5'],
            ['Windows NT', '4', '0'],
            ['Windows 98', '4', '1'],
            ['Windows Me', '4', '9'],
            ['Windows 2000', '5', '0'],
            ['Windows XP', '5', '1'],
            ['Windows Vista', '6', '0'],
            ['Windows 7', '6', '1']]

class Reports(BaseTable):
    table = 'reports'
    columns = ['id', 'client_crash_date', 'date_processed', 'uuid', 'product',
               'version', 'build', 'signature', 'url', 'install_age',
               'last_crash', 'uptime', 'cpu_name', 'cpu_info', 'reason',
               'address', 'os_name', 'os_version', 'email', 'user_id',
               'started_datetime', 'completed_datetime', 'success',
               'truncated', 'processor_notes', 'user_comments', 'app_notes',
               'distributor', 'distributor_version', 'topmost_filenames',
               'addons_checked', 'flash_version', 'hangid', 'process_type',
               'release_channel', 'productid']
    # TODO generate fake data
    rows = [['1', '2012-06-15 10:34:45-07', '2012-06-15 23:35:06.262196',
             '0ac2e16a-a718-43c0-a1a5-6bf922111017', 'WaterWolf', '1.0',
             '20120615000001', 'FakeSignature1', '', '391578', '', '25', 'x86',
             'GenuineIntel family 6 model 23 stepping 10 | 2',
             'EXCEPTION_ACCESS_VIOLATION_READ', '0x66a0665', 'Windows NT',
             '5.1.2600 Service Pack 3', '', '""', '2012-06-15 00:35:16.368154',
             '2012-06-15 00:35:18.463317', 't', 'f', '""', '', '', '', '',
             '""', 't', '9.0.124.0', '', '', 'release',
             '{waterwolf@example.org}']]
'''
1,2012-06-15 10:34:45-07,2012-06-15 23:35:06.262196,0ac2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,1.0,20120615000001,FakeSignature1,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-15 00:35:16.368154,2012-06-15 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,release,{waterwolf@example.org}
2,2012-06-15 10:34:45-07,2012-06-15 23:35:06.262196,0bc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,2.0,20120615000002,FakeSignature2,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-15 00:35:16.368154,2012-06-15 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,beta,{waterwolf@example.org}
3,2012-06-15 10:34:45-07,2012-06-15 23:35:06.262196,0cc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,3.0a2,20120615000003,FakeSignature3,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-15 00:35:16.368154,2012-06-15 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,aurora,{waterwolf@example.org}
4,2012-06-15 10:34:45-07,2012-06-15 23:35:06.262196,0dc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,4.0a1,20120615000004,FakeSignature4,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-15 00:35:16.368154,2012-06-15 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,nightly,{waterwolf@example.org}
5,2012-06-16 10:34:45-07,2012-06-16 23:35:06.262196,1ac2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,1.0,20120615000001,FakeSignature1,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-16 00:35:16.368154,2012-06-16 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,release,{waterwolf@example.org}
6,2012-06-16 10:34:45-07,2012-06-16 23:35:06.262196,1bc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,2.0,20120615000002,FakeSignature2,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-16 00:35:16.368154,2012-06-16 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,beta,{waterwolf@example.org}
7,2012-06-16 10:34:45-07,2012-06-16 23:35:06.262196,1cc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,3.0a2,20120615000003,FakeSignature3,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-16 00:35:16.368154,2012-06-16 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,aurora,{waterwolf@example.org}
8,2012-06-16 10:34:45-07,2012-06-16 23:35:06.262196,1dc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,4.0a1,20120615000004,FakeSignature4,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-16 00:35:16.368154,2012-06-16 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,nightly,{waterwolf@example.org}
'''

class OSVersions(BaseTable):
    table = 'os_versions'
    columns = ['os_version_id', 'os_name', 'major_version',
               'minor_version', 'os_version_string']
    rows = [['66', 'Windows', '6', '135', 'Windows Unknown'],
            ['67', 'Windows', '5', '3', 'Windows Unknown'],
            ['68', 'Mac OS X', '10', '8', 'OS X 10.8'],
            ['69', 'Linux', '2', '6', 'Linux'],
            ['70', 'Windows', '5', '11', 'Windows Unknown'],
            ['71', 'Windows', '6', '0', 'Windows Vista'],
            ['72', 'Windows', '6', '50', 'Windows Unknown'],
            ['73', 'Mac OS X', '10', '4', 'OS X 10.4'],
            ['74', 'Mac OS X', '300', '5', 'OS X Unknown'],
            ['75', 'Windows', '5', '0', 'Windows 2000']]

class Productdims(BaseTable):
    table = 'productdims'
    columns = ['id', 'product', 'version', 'branch', 'release', 'sort_key',
               'version_sort']
    rows = [['1', 'WaterWolf', '1.0', '2.2', 'major', '1', '001000z000000'],
            ['2', 'WaterWolf', '2.0', '2.2', 'development', '2',
               '002000z000000'],
            ['3', 'WaterWolf', '3.0a2', '2.2', 'development', '3',
               '003000z000000'],
            ['4', 'WaterWolf', '4.0a1', '2.2', 'milestone', '4',
               '004000z000000']]

class ProductProductidMap(BaseTable):
    table = 'product_productid_map'
    columns = ['product_name', 'productid', 'rewrite', 'version_began',
               'version_ended']
    rows = [['WaterWolf', '{waterwolf@example.org}', 'f', '1.0']]

class ReleaseRepositories(BaseTable):
    table = 'release_repositories'
    columns = ['repository']
    rows = [['mozilla-central'],
            ['mozilla-1.9.2'],
            ['comm-central'],
            ['comm-1.9.2'],
            ['comm-central-trunk'],
            ['mozilla-central-android'],
            ['mozilla-release'],
            ['mozilla-beta'],
            ['mozilla-aurora'],
            ['mozilla-aurora-android'],
            ['mozilla-esr10'],
            ['mozilla-esr10-android'],
            ['release']]

class CrontabberState(BaseTable):
    table = 'crontabber_state'
    columns = ['state', 'last_updated']
    rows = [["'{}'", "2012-05-16 00:00:00"]]

def main():
    # the order that tables are loaded is important.
    tables = [CrontabberState]
    tables = [DailyCrashCodes, OSNames, OSNameMatches, ProcessTypes, Products, 
              ReleaseChannels, ProductReleaseChannels, RawADU, 
              ReleaseChannelMatches, ReleasesRaw, UptimeLevels,
              WindowsVersions, Reports, OSVersions, Productdims,
              ProductProductidMap, ReleaseRepositories, CrontabberState]
    for t in tables:
        t = t()
        for insert in t.generate_inserts():
            print insert

if __name__ == '__main__':
    main()

