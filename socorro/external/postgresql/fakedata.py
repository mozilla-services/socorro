#!/usr/bin/python
#
# Generate fake data for Socorro.
#
# Products, versions, number of days to generate data for, etc. are
# configurable, and test data is randomized using configurable probability
# but deterministic (within reason.)

import datetime
import uuid
import random
import csv
import os

crash_ids = []

def date_range(start_date, end_date, delta=None):
    if delta is None:
        delta = datetime.timedelta(days=1)
    if start_date > end_date:
        raise Exception('start_date must be <= end_date')
    while start_date <= end_date:
        yield start_date
        start_date += delta

# based on http://code.activestate.com/recipes/117241


def weighted_choice(items):
    """items is a list of tuples in the form (item, weight)"""
    weight_total = sum((item[1] for item in items))
    n = random.uniform(0, weight_total)
    for item, weight in items:
        if n < weight:
            return item
        n = n - weight
    return item


class BaseTable(object):
    def __init__(self, days=None):

        # use a known seed for PRNG to get deterministic behavior.
        random.seed(5)

        self.days = days or 7
        self.end_date = datetime.datetime.utcnow()
        self.start_date = self.end_date - datetime.timedelta(self.days)

        self.releases = {
            'WaterWolf': {
                'channels': {
                    'ESR': {
                        'versions': [{
                            'number': '1.0',
                            'probability': 0.5,
                            'buildid': '%s000000'
                        }],
                        'adu': '100',
                        'repository': 'esr',
                        'throttle': '1'
                    },
                    'Release': {
                        'versions': [{
                            'number': '2.0',
                            'probability': 0.5,
                            'buildid': '%s000001'
                        }, {
                            'number': '2.1',
                            'probability': 0.5,
                            'buildid': '%s000002'
                        }],
                        'adu': '10000',
                        'repository': 'release',
                        'throttle': '0.1'
                    },
                    'Beta': {
                        'versions': [{
                            'number': '3.0',
                            'probability': 0.06,
                            'buildid': '%s000003',
                            'beta_number': '2'
                        }, {
                            'number': '3.1',
                            'probability': 0.02,
                            'buildid': '%s000004',
                            'beta_number': '1'
                        }],
                        'adu': '100',
                        'repository': 'beta',
                        'throttle': '1'
                    },
                    'Aurora': {
                        'versions': [{
                            'number': '4.0a2',
                            'probability': 0.03,
                            'buildid': '%s000005'
                        }, {
                            'number': '3.0a2',
                            'probability': 0.01,
                            'buildid': '%s000006'
                        }],
                        'adu': '100',
                        'repository': 'dev',
                        'throttle': '1'
                    },
                    'Nightly': {
                        'versions': [{
                            'number': '5.0a1',
                            'probability': 0.01,
                            'buildid': '%s000007'
                        }, {
                            'number': '4.0a1',
                            'probability': 0.001,
                            'buildid': '%s000008'
                        }],
                        'adu': '100',
                        'repository': 'dev',
                        'throttle': '1'
                    }
                },
                'crashes_per_hour': '100',
                'guid': '{waterwolf@example.com}'
            },
            'NightTrain': {
                'channels': {
                    'ESR': {
                        'versions': [{
                            'number': '1.0',
                            'probability': 0.5,
                            'buildid': '%s000010'
                        }],
                        'adu': '10',
                        'repository': 'esr',
                        'throttle': '1'
                    },
                    'Release': {
                        'versions': [{
                            'number': '2.0',
                            'probability': 0.5,
                            'buildid': '%s000011'
                        }, {
                            'number': '2.1',
                            'probability': 0.5,
                            'buildid': '%s000012'
                        }],
                        'adu': '1000',
                        'repository': 'release',
                        'throttle': '0.1'
                    },
                    'Beta': {
                        'versions': [{
                            'number': '3.0',
                            'probability': 0.06,
                            'buildid': '%s000013',
                            'beta_number': '2'
                        }, {
                            'number': '3.1',
                            'probability': 0.02,
                            'buildid': '%s000014',
                            'beta_number': '1'
                        }],
                        'adu': '10',
                        'repository': 'beta',
                        'throttle': '1'
                    },
                    'Aurora': {
                        'versions': [{
                            'number': '4.0a2',
                            'probability': 0.03,
                            'buildid': '%s000015'
                        }, {
                            'number': '3.0a2',
                            'probability': 0.01,
                            'buildid': '%s000016'
                        }],
                        'adu': '10',
                        'repository': 'dev',
                        'throttle': '1'
                    },
                    'Nightly': {
                        'versions': [{
                            'number': '5.0a1',
                            'probability': 0.01,
                            'buildid': '%s000017'
                        }, {
                            'number': '4.0a1',
                            'probability': 0.001,
                            'buildid': '%s000018'
                        }],
                        'adu': '10',
                        'repository': 'dev',
                        'throttle': '1'
                    }
                },
                'crashes_per_hour': '50',
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
            '': 0.25,
            'FakeSignature1': 0.25,
            'FakeSignature2': 0.15,
            'FakeSignature3': 0.10,
            'FakeSignature4': 0.05,
            'FakeSignature5': 0.05,
            'FakeSignature6': 0.05,
            'FakeSignature7': 0.05,
            'FakeSignature8': 0.025,
            'FakeSignature9': 0.025
        }

        self.explosive_signature = 'FakeSignature8'

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
            'plugin': 0.25,
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
        self.urls = [
            ('%s/%s' % ('http://example.com', random.getrandbits(16)), 0.7)
            for x in range(100)]

        # email address and probability.
        self.email_addresses = [
            ('socorro-%s@%s' % (random.getrandbits(16), 'restmail.net'), 0.01)
            for x in range(10)]
        self.email_addresses.append((None, 0.9))

        # crash user comments and probability.
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

    # this should be overridden when fake data is to be generated.
    # it will work for static data as-is.
    def generate_rows(self):
        return iter(self.rows)

    # this uses random instead of simply using uuid to get deterministic
    # behavior, since random is seeded
    def generate_crashid(self, timestamp):
        crashid = str(uuid.UUID(int=random.getrandbits(128)))
        depth = 0
        final_crashid = "%s%d%02d%02d%02d" % (crashid[:-7], depth, timestamp.year % 100,
                                     timestamp.month, timestamp.day)
        crash_ids.append( (final_crashid, timestamp) )
        return final_crashid

    def buildid(self, fragment, format='%Y%m%d', days=None):
        days = days or self.days
        builddate = self.end_date - datetime.timedelta(days=days)
        return fragment % builddate.strftime(format)

    # nightly and aurora have releases posted every night
    def daily_builds(self, fragment, channel, days=None):
        buildids = []
        days = days or self.days
        if channel == 'Nightly' or channel == 'Aurora':
            for day in xrange(0, self.days):
                buildids.append(self.buildid(fragment, days=day))
        else:
            buildids.append(self.buildid(fragment))
        return buildids


class OSNames(BaseTable):
    table = 'os_names'
    columns = ['os_name', 'os_short_name']
    rows = [['Windows', 'win'],
            ['Mac OS X', 'mac'],
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
    columns = ['product_name', 'sort', 'rapid_release_version',
               'release_name', 'rapid_beta_version']

    def generate_rows(self):
        for i, product in enumerate(self.releases):
            row = [product, str(i), 1.0, product.lower(), 4.0]
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
                throttle = self.releases[product][
                    'channels'][channel]['throttle']
                row = [product, channel, throttle]
                yield row


class RawADU(BaseTable):
    table = 'raw_adu'
    columns = ['adu_count', 'date', 'product_name', 'product_os_platform',
               'product_os_version', 'product_version', 'build',
               'build_channel', 'product_guid', 'received_at']

    def generate_rows(self):
        for timestamp in date_range(self.start_date, self.end_date):
            received_at = timestamp.today() - datetime.timedelta(days=1)
            for product in self.releases:
                for channel in self.releases[product]['channels']:
                    versions = self.releases[product][
                        'channels'][channel]['versions']
                    for version in versions:
                        number = version['number']
                        buildids = self.daily_builds(
                            version['buildid'], channel)
                        adu = self.releases[product][
                            'channels'][channel]['adu']
                        product_guid = self.releases[product]['guid']
                        for os_name in self.oses:
                            for buildid in buildids:
                                row = [adu, str(timestamp), product, os_name,
                                       os_name, number, buildid,
                                       channel.lower(), product_guid,
                                       str(received_at)]
                                yield row


class ReleaseChannelMatches(BaseTable):
    table = 'release_channel_matches'
    columns = ['release_channel', 'match_string']
    rows = [['Release', 'release'],
            ['Release', 'default'],
            ['Beta', 'beta'],
            ['Aurora', 'aurora'],
            ['Nightly', 'nightly%']]


class ReleasesRaw(BaseTable):
    table = 'releases_raw'
    columns = ['product_name', 'version', 'platform', 'build_id',
               'build_type', 'beta_number', 'repository']

    def generate_rows(self):
        for product in self.releases:
            for channel in self.releases[product]['channels']:
                for os_name in self.oses:
                    versions = self.releases[product][
                        'channels'][channel]['versions']
                    for version in versions:
                        buildids = self.daily_builds(
                            version['buildid'], channel)

                        number = version['number']
                        if 'esr' in number:
                            number = number.split('esr')[0]
                        beta_number = 0
                        if 'beta_number' in version:
                            beta_number = version['beta_number']
                        repository = self.releases[product][
                            'channels'][channel]['repository']
                        build_type = channel
                        if channel == 'esr':
                            build_type = 'Release'

                        for buildid in buildids:
                            row = [product.lower(), number, os_name,
                                   buildid, build_type, beta_number,
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
               'release_channel', 'productid', 'exploitability']

    def generate_rows(self):
        count = 0
        for product in self.releases:
            cph = self.releases[product]['crashes_per_hour']
            delta = datetime.timedelta(minutes=(60.0 / int(cph)))
            for timestamp in date_range(self.start_date, self.end_date, delta):
                choices = []
                for channel in self.releases[product]['channels']:
                    versions = self.releases[product][
                        'channels'][channel]['versions']
                    adu = self.releases[product]['channels'][channel]['adu']
                    for version in versions:
                        probability = float(version['probability'])
                        self.releases[product]['channels'][
                            channel]['name'] = channel
                        choice = (version, adu, channel)
                        choices.append((choice, probability))

                (version, adu, channel_name) = weighted_choice(choices)
                number = version['number']
                buildids = self.daily_builds(version['buildid'], channel_name)
                product_guid = self.releases[product]['guid']
                # TODO enumerate correct values
                exploitability = 'medium'
                flash_process_dump = None

                for os_name in self.oses:
                    # TODO need to review, want to fake more of these
                    client_crash_date = timestamp.strftime(
                        '%Y-%m-%d %H:%M:%S+00:00')
                    date_processed = str(timestamp)
                    signature = weighted_choice([(
                        x, self.signatures[x]) for x in self.signatures])

                    now = datetime.datetime.now()
                    amt = 1
                    if (signature == self.explosive_signature and
                        timestamp.date() == now.date()):
                        amt = 5

                    for i in xrange(amt):
                        url = weighted_choice(self.urls)
                        install_age = '1234'
                        last_crash = '1234'
                        uptime = '1234'
                        cpu_name = 'x86'
                        cpu_info = '...'
                        reason = weighted_choice([
                            (x, self.crash_reasons[x])
                            for x in self.crash_reasons
                        ])
                        address = '0xdeadbeef'
                        os_version = '1.2.3.4'
                        email = weighted_choice(self.email_addresses)
                        user_id = ''
                        started_datetime = str(timestamp)
                        completed_datetime = str(timestamp)
                        success = 't'
                        truncated = 'f'
                        processor_notes = '...'
                        user_comments = None
                        # if there is an email, always include a comment
                        if email:
                            user_comments = weighted_choice([
                                (x, self.comments[x])
                                for x in self.comments
                            ])
                        app_notes = ''
                        distributor = ''
                        distributor_version = ''
                        topmost_filenames = ''
                        addons_checked = 'f'
                        flash_version = weighted_choice([
                            (x, self.flash_versions[x])
                            for x in self.flash_versions])
                        hangid = ''
                        process_type = weighted_choice([
                            (x, self.process_types[x])
                            for x in self.process_types])

                        for buildid in buildids:
                            row = [
                                    str(count),
                                    client_crash_date,
                                    date_processed,
                                    self.generate_crashid(timestamp),
                                    product,
                                    number,
                                    buildid,
                                    signature,
                                    url,
                                    install_age,
                                    last_crash,
                                    uptime,
                                    cpu_name,
                                    cpu_info,
                                    reason,
                                    address,
                                    os_name,
                                    os_version,
                                    email,
                                    user_id,
                                    started_datetime,
                                    completed_datetime,
                                    success,
                                    truncated,
                                    processor_notes,
                                    user_comments,
                                    app_notes,
                                    distributor,
                                    distributor_version,
                                    topmost_filenames,
                                    addons_checked,
                                    flash_version,
                                    hangid,
                                    process_type,
                                    channel_name,
                                    product_guid,
                                    exploitability
                                  ]

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
    rows = [['WaterWolf', '{waterwolf@example.org}', 'f', '1.0', '1.0']]


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
    columns = ['last_updated', 'state']
    rows = [['2012-05-16 00:00:00', '{}']]


class CrashTypes(BaseTable):
    table = 'crash_types'
    columns = [
        'crash_type_id', 'crash_type', 'crash_type_short', 'process_type',
        'has_hang_id', 'old_code', 'include_agg']
    rows = [['1', 'Browser', 'crash', 'browser', False, 'C', True],
            ['2', 'OOP Plugin', 'oop', 'plugin', False, 'P', True],
            ['3', 'Hang Browser', 'hang-b', 'plugin', True, 'c', False],
            ['4', 'Hang Plugin', 'hang-p', 'browser', True, 'p', True],
            ['5', 'Content', 'content', 'content', False, 'T', True]]


class ReportPartitionInfo(BaseTable):
    table = 'report_partition_info'
    columns = ['table_name', 'build_order', 'keys', 'indexes',
               'fkeys', 'partition_column']
    rows = [['reports', '1', '{id,uuid}',
             '{date_processed,hangid,"product,version",reason,signature,url}',
             '{}', 'date_processed'],
            ['plugins_reports', '2', '{"report_id,plugin_id"}',
             '{"report_id,date_processed"}',
             ('{"(plugin_id) REFERENCES plugins(id)","(report_id)'
              ' REFERENCES reports_WEEKNUM(id)"}'), 'date_processed'],
            ['extensions', '3', '{"report_id,extension_key"}',
             '{"report_id,date_processed"}',
             '{"(report_id) REFERENCES reports_WEEKNUM(id)"}',
             'date_processed'],
            ['raw_crashes', '4', '{uuid}', '{}', '{}', 'date_processed'],
            ['signature_summary_installations', '5',
             '{"signature_id,product_name,version_string,report_date"}',
            '{}',
            '{"(signature_id) REFERENCES signatures(signature_id)"}', 'report_date' ]]


class Skiplist(BaseTable):
    table = 'skiplist'
    columns = ['category', 'rule']
    rows = [['ignore','everything'],
            ['prefix','SocketShutdown']]

class RawCrashes(BaseTable):
    table = 'raw_crashes'
    columns = ['uuid', 'raw_crash', 'date_processed']

    def generate_rows(self):
        for crashid, date_processed, in crash_ids:
            raw_crash = '{ "uuid": "%s", "IsGarbageCollecting": "1" }' % crashid
            row = [crashid, raw_crash, date_processed]
            yield row


# the order that tables are loaded is important.
tables = [OSNames, OSNameMatches, ProcessTypes, Products, ReleaseChannels,
          ProductReleaseChannels, RawADU, ReleaseChannelMatches,
          ReleasesRaw, UptimeLevels, WindowsVersions, Reports, RawCrashes, OSVersions,
          ProductProductidMap, ReleaseRepositories, CrontabberState,
          CrashTypes, ReportPartitionInfo, Skiplist]

# FIXME this could be built up from BaseTable's releases dict, instead
featured_versions = ('5.0a1', '4.0a2', '3.1b1', '2.1')
