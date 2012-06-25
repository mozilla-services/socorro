#!/usr/bin/python

import datetime
import uuid
import random

class BaseTable(object):
    def __init__(self):

        # use a known seed for PRNG to get deterministic behavior.
        random.seed(5)

        # TODO should be configurable
        self.end_date = datetime.datetime.today()

        # TODO should be configurable
        self.start_date = self.end_date - datetime.timedelta(days=30)

        self.releases = {
            'WaterWolf': {
                'channels': {
                    'ESR': {
                        'versions': [{
                            'number': '1.0',
                            'probability': 0.5
                        }],
                        'adu': '100',
                        'repository': 'esr',
                        'throttle': '1'
                    },
                    'Release': {
                        'versions': [{
                            'number': '2.0',
                            'probability': 0.5
                        },{
                            'number': '2.1',
                            'probability': 0.5
                        }],
                        'adu': '10000',
                        'repository': 'release',
                        'throttle': '0.1'
                    },
                    'Beta': {
                        'versions': [{
                            'number': '3.0',
                            'probability': 0.06,
                            'beta_number': '2'
                        },{
                            'number': '3.1',
                            'probability': 0.02,
                            'beta_number': '1'
                        }],
                        'adu': '100',
                        'repository': 'beta',
                        'throttle': '1'
                    },
                    'Aurora': {
                        'versions': [{
                            'number': '4.0a2',
                            'probability': 0.03
                        },{
                            'number': '3.0a2',
                            'probability': 0.01
                        }],
                        'adu': '100',
                        'repository': 'dev',
                        'throttle': '1'
                    },
                    'Nightly': {
                        'versions': [{
                            'number': '5.0a1',
                            'probability': 0.01
                        },{
                            'number': '4.0a1',
                            'probability': 0.001
                        }],
                        'adu': '100',
                        'repository': 'dev',
                        'throttle': '1'
                    }
                },
                'crashes_per_hour': '10',
                'guid': '{waterwolf@example.com}'
            },
            'Nighttrain': {
                'channels': {
                    'ESR': {
                        'versions': [{
                            'number': '1.0',
                            'probability': 0.5
                        }],
                        'adu': '10',
                        'repository': 'esr',
                        'throttle': '1'
                    },
                    'Release': {
                        'versions': [{
                            'number': '2.0',
                            'probability': 0.5
                        },{
                            'number': '2.1',
                            'probability': 0.5
                        }],
                        'adu': '1000',
                        'repository': 'release',
                        'throttle': '0.1'
                    },
                    'Beta': {
                        'versions': [{
                            'number': '3.0',
                            'probability': 0.06,
                            'beta_number': '2'
                        },{
                            'number': '3.1',
                            'probability': 0.02,
                            'beta_number': '1'
                        }],
                        'adu': '10',
                        'repository': 'beta',
                        'throttle': '1'
                    },
                    'Aurora': {
                        'versions': [{
                            'number': '4.0a2',
                            'probability': 0.03
                        },{
                            'number': '3.0a2',
                            'probability': 0.01
                        }],
                        'adu': '10',
                        'repository': 'dev',
                        'throttle': '1'
                    },
                    'Nightly': {
                        'versions': [{
                            'number': '5.0a1',
                            'probability': 0.01
                        },{
                            'number': '4.0a1',
                            'probability': 0.001
                        }],
                        'adu': '10',
                        'repository': 'dev',
                        'throttle': '1'
                    }
                },
                'crashes_per_hour': '1',
                'guid': '{nighttrain@example.com}'
            }
        }

        self.oses = {
            'Linux': {
                'short_name': 'lin',
                'versions': {
                    'Linux': {
                        'major': '2',
                        'minor': '6'}
                }
            },
            'Mac OS X': {
                'short_name': 'mac',
                'versions': {
                    'OS X 10.8': {
                        'major': '10',
                        'minor': '8'
                    }
                }
            },
            'Windows': {
                'short_name': 'win',
                'versions': {
                    'Windows NT(4)': {
                        'major': '3',
                        'minor': '5'
                    },
                    'Windows NT(3)': {
                        'major': '4',
                        'minor': '0'
                    },
                    'Windows 98': {
                        'major': '4',
                        'minor': '1'
                    },
                    'Windows Me': {
                        'major': '4',
                        'minor': '9'
                    },
                    'Windows 2000': {
                        'major': '4',
                        'minor': '1'
                    },
                    'Windows XP': {
                        'major': '5',
                        'minor': '1'
                    },
                    'Windows Vista': {
                        'major': '6',
                        'minor': '0'
                    },
                    'Windows 7': {
                        'major': '6',
                        'minor': '1'
                    }
                }
            }
        }

        # signature name and probability.
        self.signatures = {
            '':                0.25,
            'FakeSignature1':  0.25,
            'FakeSignature2':  0.15,
            'FakeSignature3':  0.10,
            'FakeSignature4':  0.05,
            'FakeSignature5':  0.05,
            'FakeSignature6':  0.05,
            'FakeSignature7':  0.05,
            'FakeSignature8':  0.025,
            'FakeSignature9':  0.025
        }

        # flash version and probability.
        self.flash_versions = {
            '1.1.1.1': 0.25,
            '1.1.1.2': 0.25,
            '1.1.1.3': 0.25,
            '1.1.1.4': 0.25
        }

        # crash type and probability.
        self.process_types = {
            'browser': 0.5,
            'plugin':  0.25,
            'content': 0.25
        }

        # crash reason and probability.
        self.crash_reasons = {
            'reason0': 0.1,
            'reason1': 0.1,
            'reason2': 0.1,
            'reason3': 0.1,
            'reason4': 0.1,
            'reason5': 0.1,
            'reason6': 0.1,
            'reason7': 0.1,
            'reason8': 0.1,
            'reason9': 0.1
        }

        # URL and probability.
        self.urls = [('%s/%s' % ('http://example.com', random.getrandbits(16)), 0.7) for x in range(100)]

        # email address and probability.
        self.email_addresses = [('%s@%s' % (random.getrandbits(16), 'example.com'), 0.01) for x in range(10)]
        self.email_addresses.append(('', 0.9))

        # crash reason and probability.
        self.comments = {
            'comment0': 0.1,
            'comment1': 0.1,
            'comment2': 0.1,
            'comment3': 0.1,
            'comment4': 0.1,
            'comment5': 0.1,
            'comment6': 0.1,
            'comment7': 0.1,
            'comment8': 0.1,
            'comment9': 0.1
        }

        self.insertSQL = 'INSERT INTO %s (%s) VALUES (%s)'

    # this should be overridden when fake data is to be generated.
    # it will work for static data as-is.
    def generate_rows(self):
        for row in self.rows:
            yield row

    def generate_inserts(self):
        for row in self.generate_rows():
            yield self.insertSQL % (self.table, ', '.join(self.columns),
                                    "'" + "', '".join(row) + "'") + ';'

    def date_to_buildid(self, timestamp):
        return timestamp.strftime('%Y%m%d%H%M%S')

    def generate_crashid(self, timestamp):
        crashid = str(uuid.UUID(int=random.getrandbits(128)))
        depth = 0
        return "%s%d%02d%02d%02d" % (crashid[:-7], depth, timestamp.year%100,
                                     timestamp.month, timestamp.day)

    def date_range(self, start_date, end_date, delta=None):
        if delta is None:
            delta = datetime.timedelta(days=1)
        if start_date > end_date:
            raise Exception('start_date must be <= end_date')
        while start_date <= end_date:
            yield start_date
            start_date += delta

    # based on http://code.activestate.com/recipes/117241
    def weighted_choice(self, items):
        """items is a list of tuples in the form (item, weight)"""
        weight_total = sum((item[1] for item in items))
        n = random.uniform(0, weight_total)
        for item, weight in items:
            if n < weight:
                return item
            n = n - weight
        return item


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
            row = [product, str(i), '1.0', product.lower()]
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
        for product in self.releases:
            for channel in self.releases[product]['channels']:
                throttle = self.releases[product]['channels'][channel]['throttle']
                row = [product, channel, throttle]
                yield row

class RawADU(BaseTable):
    table = 'raw_adu'
    columns = ['adu_count', 'date', 'product_name', 'product_os_platform',
               'product_os_version', 'product_version', 'build',
               'build_channel', 'product_guid']

    def generate_rows(self):
        for timestamp in self.date_range(self.start_date, self.end_date):
            buildid = self.date_to_buildid(timestamp)
            for product in self.releases:
                for channel in self.releases[product]['channels']:
                    versions = self.releases[product]['channels'][channel]['versions']
                    for version in versions:
                        number = version['number']
                        adu = self.releases[product]['channels'][channel]['adu']
                        product_guid = self.releases[product]['guid']
                        for os_name in self.oses:
                            row = [adu, str(timestamp), product, os_name,
                                   os_name, number,
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
        for timestamp in self.date_range(self.start_date, self.end_date):
            buildid = self.date_to_buildid(timestamp)
            for product in self.releases:
                for channel in self.releases[product]['channels']:
                    for os_name in self.oses:
                        versions = self.releases[product]['channels'][channel]['versions']
                        for version in versions:
                            number = version['number']
                            beta_number = '0'
                            if 'beta_number' in version:
                                beta_number = version['beta_number']
                            repository = self.releases[product]['channels'][channel]['repository']
                            row = [product.lower(), number, os_name,
                                   buildid, channel, beta_number,
                                   repository]
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
        count = 0
        for product in self.releases:
            cph = self.releases[product]['crashes_per_hour']
            # 5 is the number of channels, since only one channel will be
            # randomly chosen per interval.
            delta = datetime.timedelta(minutes=(60.0 / int(cph)) * 5)
            for timestamp in self.date_range(self.start_date, self.end_date, delta):
                buildid = self.date_to_buildid(timestamp)
                choices = []
                for channel in self.releases[product]['channels']:
                    versions = self.releases[product]['channels'][channel]['versions']
                    for version in versions:
                        probability = float(version['probability'])
                        self.releases[product]['channels'][channel]['name'] = channel
                        choices.append((self.releases[product]['channels'][channel], probability))

                channel = self.weighted_choice(choices)
                versions = channel['versions']
                number = version['number']
                adu = channel['adu']
                product_guid = self.releases[product]['guid']
                for os_name in self.oses:
                    # TODO need to review, want to fake more of these
                    client_crash_date = str(timestamp)
                    date_processed = str(timestamp)
                    signature = self.weighted_choice([(x,self.signatures[x]) for x in self.signatures])
                    url = self.weighted_choice(self.urls)
                    install_age = '1234'
                    last_crash = '1234'
                    uptime = '1234'
                    cpu_name = 'x86'
                    cpu_info = '...'
                    reason = '...'
                    address = '0xdeadbeef'
                    os_version = '1.2.3.4'
                    email = self.weighted_choice(self.email_addresses)
                    user_id = ''
                    started_datetime = str(timestamp)
                    completed_datetime = str(timestamp)
                    success = 't'
                    truncated = 'f'
                    processor_notes = '...'
                    user_comments = ''
                    if email:
                        user_comments = self.weighted_choice([(x,self.comments[x]) for x in self.comments])
                    app_notes = ''
                    distributor = ''
                    distributor_version = ''
                    topmost_filenames = ''
                    addons_checked = 'f'
                    flash_version = '1.2.3.4'
                    hangid = ''
                    process_type = 'browser'
                    row = [str(count), client_crash_date, date_processed,
                           self.generate_crashid(self.end_date), product, number,
                           self.date_to_buildid(self.end_date), signature, url,
                           install_age, last_crash, uptime, cpu_name,
                           cpu_info, reason, address, os_name, os_version, email,
                           user_id, started_datetime, completed_datetime, success,
                           truncated, processor_notes, user_comments, app_notes,
                           distributor, distributor_version, topmost_filenames,
                           addons_checked, flash_version, hangid, process_type,
                           channel['name'], product_guid]
                    yield row
                    count += 1

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
    # TODO worth faking this table?
    rows = [['WaterWolf', '{waterwolf@example.org}', 'f', '1.0', '']]

class ReleaseRepositories(BaseTable):
    table = 'release_repositories'
    columns = ['repository']
    rows = [['dev'],
            ['beta'],
            ['release'],
            ['esr'],
            ['other-dev'],
            ['other-beta'],
            ['other-release'],
            ['other-esr']]

class CrontabberState(BaseTable):
    table = 'crontabber_state'
    columns = ['state', 'last_updated']
    rows = [['{}', '2012-05-16 00:00:00']]

def main():
    # the order that tables are loaded is important.
    tables = [DailyCrashCodes, OSNames, OSNameMatches, ProcessTypes, Products,
              ReleaseChannels, ProductReleaseChannels, RawADU,
              ReleaseChannelMatches, ReleasesRaw, UptimeLevels,
              WindowsVersions, Reports, OSVersions, #ProductProductidMap,
              ReleaseRepositories, CrontabberState]
    for t in tables:
        t = t()
        for insert in t.generate_inserts():
            print insert

if __name__ == '__main__':
    main()

