#!/usr/bin/python

import datetime
import uuid

class BaseTable(object):
    def __init__(self):
        # TODO make this configurable
        self.end_date = datetime.datetime.today()
        # TODO make days configurable
        self.start_date = self.end_date - datetime.timedelta(days=30)
        self.releases = {'WaterWolf': {
                             'channels': {'ESR': {
                                              'version': '1.0',
                                              'adu': '10000'},
                                          'Release': { 
                                              'version': '2.0',
                                              'adu': '1000'},
                                          'Beta': {
                                              'version': '3.0',
                                              'adu': '100'},
                                          'Aurora': {
                                              'version': '4.0a2',
                                              'adu': '10'},
                                          'Nightly': {
                                              'version': '5.0a1',
                                              'adu': '1'}},
                             'guid': '{waterwolf@example.com}'},
                         'Nighttrain': {
                             'channels': {'ESR': {
                                              'version': '1.0',
                                              'adu': '10000'},
                                          'Release': { 
                                              'version': '2.0',
                                              'adu': '1000'},
                                          'Beta': {
                                              'version': '3.0',
                                              'adu': '100'},
                                          'Aurora': {
                                              'version': '4.0a2',
                                              'adu': '10'},
                                          'Nightly': {
                                              'version': '5.0a1',
                                              'adu': '1'}},
                             'guid': '{nighttrain@example.com}'}}
        self.oses = {'Linux': { 'short_name': 'lin',
                                'versions': { 'Linux': {'major': '2',
                                                        'minor': '6'}}},
                     'Mac OS X': { 'short_name': 'mac',
                                   'versions': { 'OS X 10.8': {'major': '10',
                                                               'minor': '8'}}},
                     'Windows': { 'short_name': 'win',
                                  'versions': {'Windows NT(4)': {'major': '3',
                                                                 'minor': '5'},
                                               'Windows NT(3)': {'major': '4',
                                                                 'minor': '0'},
                                               'Windows 98': {'major': '4',
                                                              'minor': '1'},
                                               'Windows Me': {'major': '4',
                                                              'minor': '9'},
                                               'Windows 2000': {'major': '4',
                                                                'minor': '1'},
                                               'Windows XP': {'major': '5',
                                                              'minor': '1'},
                                               'Windows Vista': {'major': '6',
                                                                 'minor': '0'},
                                               'Windows 7': {'major': '6',
                                                             'minor': '1'}}}}
        self.insertSQL = 'INSERT INTO %s (%s) VALUES (%s)'
    
    # this should be overridden when fake data is to be generated.
    # it will work for static data as-is.
    def generate_rows(self):
        for row in self.rows:
            yield row

    def generate_inserts(self):
        for row in self.generate_rows():
            print row
            yield self.insertSQL % (self.table, ', '.join(self.columns),
                                    '"' + '", "'.join(row) + '"')

    def date_to_buildid(self, timestamp):
        return timestamp.strftime('%Y%m%d%H%M%S')

    def generate_crashid(self, timestamp):
        crashid = str(uuid.uuid4())
        depth = 0
        return "%s%d%02d%02d%02d" % (crashid[:-7], depth, timestamp.year%100,
                                     timestamp.month, timestamp.day)

    def date_range(self, start_date, end_date):
        if start_date > end_date: 
            raise Exception('start_date must be <= to end_date')
        while start_date <= end_date:
            yield start_date
            start_date += datetime.timedelta(days=1)

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
    
    def generate_rows(self):
        for i, product in enumerate(self.releases):
            for channel in self.releases[product]['channels']:
                version = self.releases[product]['channels'][channel]['version']
                row = [product, str(i), version, product.lower()]
                yield row

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

    def generate_rows(self):
        for i, product in enumerate(self.releases):
            for channel in self.releases[product]['channels']:
                version = self.releases[product]['channels'][channel]['version']
                row = [product, channel, version]
                yield row

class RawADU(BaseTable):
    table = 'raw_adu'
    columns = ['adu_count', 'date', 'product_name', 'product_os_platform',
               'product_os_version', 'product_version', 'build',
               'build_channel', 'product_guid']

    def generate_rows(self):
        for timestamp in self.date_range(self.start_date, self.end_date):
            buildid = self.date_to_buildid(timestamp)
            for i, product in enumerate(self.releases):
                for channel in self.releases[product]['channels']:
                    version = self.releases[product]['channels'][channel]['version']
                    adu = self.releases[product]['channels'][channel]['adu']
                    product_guid = self.releases[product]['guid']
                    for os_name in self.oses:
                        row = [adu, str(timestamp), product, os_name,
                               os_name, version,
                               self.date_to_buildid(self.end_date),
                               channel.lower(), product_guid]
                        yield row

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

    def generate_rows(self):
        row = ['waterwolf', '1.0', 'linux',
                 self.date_to_buildid(self.end_date), 'Release', '',
                 'mozilla-release']
        yield row

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

    def generate_rows(self):
        for timestamp in self.date_range(self.start_date, self.end_date):
            buildid = self.date_to_buildid(timestamp)
            for i, product in enumerate(self.releases):
                for channel in self.releases[product]['channels']:
                    version = self.releases[product]['channels'][channel]['version']
                    adu = self.releases[product]['channels'][channel]['adu']
                    product_guid = self.releases[product]['guid']
                    for os_name in self.oses:
                        # TODO need to review, want to fake more of these
                        client_crash_date = str(timestamp)
                        date_processed = str(timestamp)
                        signature = 'fakesignature1'
                        url = ''
                        install_age = '1234'
                        last_crash = '1234'
                        uptime = '1234'
                        cpu_name = 'x86'
                        cpu_info = '...'
                        reason = '...'
                        address = '0xdeadbeef'
                        os_version = '1.2.3.4'
                        email = ''
                        user_id = ''
                        started_datetime = str(timestamp)
                        completed_datetime = str(timestamp)
                        success = 't'
                        truncated = 'f'
                        processor_notes = '...'
                        user_comments = ''
                        app_notes = ''
                        distributor = ''
                        distributor_version = ''
                        topmost_filenames = ''
                        addons_checked = 'f'
                        flash_version = '1.2.3.4'
                        hangid = ''
                        process_type = 'browser'
                        row = [str(i), client_crash_date, date_processed,
                               self.generate_crashid(self.end_date), product, version,
                               self.date_to_buildid(self.end_date), signature, url,
                               install_age, last_crash, uptime, cpu_name,
                               cpu_info, reason, address, os_name, os_version, email,
                               user_id, started_datetime, completed_datetime, success,
                               truncated, processor_notes, user_comments, app_notes,
                               distributor, distributor_version, topmost_filenames,
                               addons_checked, flash_version, hangid, process_type,
                               channel, product_guid]
                        yield row


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
    tables = [DailyCrashCodes, OSNames, OSNameMatches, ProcessTypes, Products, 
              ReleaseChannels, ProductReleaseChannels, RawADU, 
              ReleaseChannelMatches, ReleasesRaw, UptimeLevels,
              WindowsVersions, Reports, OSVersions, ProductProductidMap,
              ReleaseRepositories, CrontabberState]
    for t in tables:
        t = t()
        for insert in t.generate_inserts():
            print insert

if __name__ == '__main__':
    main()

