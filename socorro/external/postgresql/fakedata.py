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
import json

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
                            'buildid': '%s000099',
                            'beta_number': '99'
                        }, {
                            'number': '3.0',
                            'probability': 0.06,
                            'buildid': '%s000015',
                            'beta_number': '1'
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
            },
            'B2G': {
                'channels': {
                    'Nightly': {
                        'versions': [{
                            'number': '18.0',
                            'probability': 0.5,
                            'buildid': '%s000020'
                        }],
                        'adu': '10',
                        'repository': 'nightly',
                        'throttle': '1',
                        'update_channel': 'nightly',
                    },
                    'Default': {
                        'versions': [{
                            'number': '18.0',
                            'probability': 0.1,
                            'buildid': '%s000021'
                        }],
                        'adu': '10',
                        'repository': 'nightly',
                        'throttle': '1',
                        'update_channel': 'default',
                    }
                },
                'crashes_per_hour': '50',
                'guid': '{b2g@example.com}'
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
        final_crashid = "%s%d%02d%02d%02d" % (crashid[:-7],
                                              depth,
                                              timestamp.year % 100,
                                              timestamp.month,
                                              timestamp.day)
        crash_ids.append((final_crashid, timestamp))
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


class Products(BaseTable):
    table = 'products'
    columns = ['product_name', 'sort', 'rapid_release_version',
               'release_name', 'rapid_beta_version']

    def generate_rows(self):
        for i, product in enumerate(self.releases):
            row = [product, str(i), 1.0, product.lower(), 3.0]
            yield row


class ProductBuildTypes(BaseTable):
    table = 'product_build_types'  # replaces product_release_channels
    columns = ['product_name', 'build_type', 'throttle']

    def generate_rows(self):
        for product in self.releases:
            for channel in self.releases[product]['channels']:
                if channel == 'Default':
                    continue
                throttle = self.releases[product][
                    'channels'][channel]['throttle']
                row = [product, channel.lower(), throttle]
                yield row


# DEPRECATED
class ProductReleaseChannels(BaseTable):
    table = 'product_release_channels'
    columns = ['product_name', 'release_channel', 'throttle']

    def generate_rows(self):
        for product in self.releases:
            for channel in self.releases[product]['channels']:

                # FIXME hackaround for B2G
                if product == 'B2G' and channel == 'Nightly':
                    channel = 'Release'
                    throttle = '1'
                else:
                    if channel == 'Default':
                        continue
                    throttle = self.releases[product][
                        'channels'][channel]['throttle']

                row = [product, channel, throttle]
                yield row


class RawADI(BaseTable):
    table = 'raw_adi'
    columns = ['adi_count', 'date', 'product_name', 'product_os_platform',
               'product_os_version', 'product_version', 'build',
               'product_guid', 'received_at', 'update_channel']

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
                                       product_guid, str(received_at),
                                       channel.lower()]
                                yield row


class ReleasesRaw(BaseTable):
    table = 'releases_raw'
    columns = ['product_name', 'version', 'platform', 'build_id',
               'update_channel', 'beta_number', 'repository',
               'build_type', 'version_build']

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
                        update_channel = channel
                        if channel == 'esr':
                            update_channel = 'Release'
                        version_build = beta_number
                        if channel == 'beta' and version['beta_number'] == 99:
                            version_build = 'build1'

                        for buildid in buildids:
                            row = [product.lower(), number, os_name,
                                   buildid, update_channel.lower(),
                                   beta_number, repository,
                                   update_channel.lower(),
                                   version_build]
                            yield row


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
               'release_channel', 'productid', 'exploitability',
               'update_channel']

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
                            row = [str(count),
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
                                   exploitability,
                                   channel_name]

                            yield row
                            count += 1


class ProductProductidMap(BaseTable):
    table = 'product_productid_map'
    columns = ['product_name', 'productid', 'rewrite', 'version_began',
               'version_ended']
    rows = [['WaterWolf', '{waterwolf@example.org}', 'f', '1.0', '1.0'],
            ['B2G', '{3c2e2abc-06d4-11e1-ac3b-374f68613e61}', 'f', '1.0', '1.0']]


class RawCrashes(BaseTable):
    table = 'raw_crashes'
    columns = ['uuid', 'raw_crash', 'date_processed']

    def generate_rows(self):
        vendors = [u'0x8086', u'0x1002', u'0x10de']
        devices = [u'0x2972', u'0x9804', u'0xa011']
        android = [
            {
                'manufacturer': 'samsung',
                'model': 'GT-P5100',
                'android_version': '16 (REL)',
                'cpu_abi': ' armeabi-v7a',
                'b2g_os_version': '1.0.1.0-prerelease',
                'product_name': 'B2G',
                'release_channel': 'nightly',
                'version': '18.0'
            },
            {
                'manufacturer': 'asus',
                'model': 'Nexus 7',
                'android_version': '15 (REL)',
                'cpu_abi': ' armeabi-v7a',
                'b2g_os_version': '1.0.1.0-prerelease',
                'product_name': 'B2G',
                'release_channel': 'nightly',
                'version': '18.0'
            },
            {
                'manufacturer': 'samsung',
                'model': ' GT-N8020',
                'android_version': '16 (REL)',
                'cpu_abi': ' armeabi-v7a',
                'b2g_os_version': '1.0.1.0-prerelease',
                'product_name': 'B2G',
                'release_channel': 'nightly',
                'version': '18.0'
            },
            {
                'manufacturer': 'ZTE',
                'model': ' roamer2',
                'android_version': '15 (REL)',
                'cpu_abi': ' armeabi-v7a',
                'b2g_os_version': '1.0.1.0-prerelease',
                'product_name': 'B2G',
                'release_channel': 'nightly',
                'version': '18.0'
            },
        ]
        for crashid, date_processed, in crash_ids:
            android_device = random.choice(android)
            raw_crash = {
                "uuid": crashid,
                "IsGarbageCollecting": "1",
                "AdapterVendorID": random.choice(vendors),
                "AdapterDeviceID": random.choice(devices),
                "Android_CPU_ABI": android_device['cpu_abi'],
                "Android_Manufacturer": android_device['manufacturer'],
                "Android_Model": android_device['model'],
                "Android_Version": android_device['android_version'],
                "B2G_OS_Version": android_device['b2g_os_version'],
                "ProductName": android_device['product_name'],
                "ReleaseChannel": android_device['release_channel'],
                "Version": android_device['version']
            }
            row = [crashid, json.dumps(raw_crash), date_processed]
            yield row


class UpdateChannelMap(BaseTable):
    table = 'update_channel_map'
    columns = ['update_channel', 'productid', 'version_field', 'rewrite']

    def generate_rows(self):
        buildids = self.daily_builds('%s000020', 'Nightly')
        rewrite = {
            "Android_Manufacturer": "ZTE",
            "Android_Model": " roamer2",
            "Android_Version": "15 (REL)",
            "B2G_OS_Version": "1.0.1.0-prerelease",
            "BuildID": buildids,
            "ProductName": "B2G",
            "ReleaseChannel": "nightly",
            "Version": "18.0",
            "rewrite_update_channel_to": "release-zte",
            "rewrite_build_type_to": "release"
        }

        row = [['nightly', '{3c2e2abc-06d4-11e1-ac3b-374f68613e61}',
               'B2G_OS_Version', json.dumps(rewrite)]]
        return row


class ProcessedCrashes(BaseTable):
    table = 'processed_crashes'
    columns = ['uuid', 'processed_crash', 'date_processed']

    def generate_rows(self):
        for crashid, date_processed, in crash_ids:
            processed_crash = {
                "ReleaseChannel": "release",
                "Winsock_LSP": "",
                "additional_minidumps": [],
                "addons": [
                    [
                        "WebSiteRecommendation@weliketheweb.com",
                        "1.1.1"
                    ],
                    [
                        "{972ce4c6-7e08-4474-a285-3208198ce6fd}",
                        "24.3.0"
                    ]
                ],
                "addons_checked": True,
                "address": "0x60943b3c",
                "app_notes": None,
                "build": "20140131092626",
                "client_crash_date": "2014-02-18 23:59:36.000000",
                "completeddatetime": "2014-02-19 00:00:17.670013",
                "cpu_info": "GenuineIntel family 6 model 58 stepping 9 | 4",
                "cpu_name": "x86",
                "crash_time": 1392767976,
                "crashedThread": 0,
                "date_processed": None, #FIXME
                "distributor": None,
                "distributor_version": None,
                "dump": "",
                "email": None,
                "exploitability": "low",
                "flash_version": "[blank]",
                "hang_type": 0,
                "hangid": None,
                "install_age": 754083,
                "java_stack_trace": None,
                "json_dump": {
                    "crash_info": {
                        "address": "0x60943b3c",
                        "crashing_thread": 0,
                        "type": "EXCEPTION_ACCESS_VIOLATION_READ"
                    },
                    "crashing_thread": {
                        "frames": [
                            {
                                "file": "f:/dd/vctools/crt_bld/SELF_X86/crt/src/INTEL/memcpy.asm",
                                "frame": 0,
                                "function": "memcpy",
                                "function_offset": "0x154",
                                "line": 319,
                                "module": "msvcr100.dll",
                                "module_offset": "0x1fd4",
                                "offset": "0x6ce51fd4",
                                "trust": "context"
                            },
                            {
                                "file": "hg:hg.mozilla.org/releases/mozilla-esr24:xpcom/string/src/nsTSubstring.cpp:d06a17a96fa2",
                                "frame": 1,
                                "function": "nsACString_internal::Assign(nsCSubstringTuple const &,mozilla::fallible_t const &)",
                                "function_offset": "0xa4",
                                "line": 416,
                                "module": "xul.dll",
                                "module_offset": "0xe2884",
                                "offset": "0x63892884",
                                "trust": "frame_pointer"
                            },
                            {
                                "file": "hg:hg.mozilla.org/releases/mozilla-esr24:xpcom/string/src/nsTSubstring.cpp:d06a17a96fa2",
                                "frame": 2,
                                "function": "nsACString_internal::Assign(nsCSubstringTuple const &)",
                                "function_offset": "0x6",
                                "line": 392,
                                "module": "xul.dll",
                                "module_offset": "0x1293ac",
                                "offset": "0x638d93ac",
                                "trust": "cfi"
                            }
                        ],
                        "threads_index": 0,
                        "total_frames": 2
                    },
                    "largest_free_vm_block": "0x70df0000",
                    "main_module": 0,
                    "modules": [
                        {
                            "base_addr": "0x950000",
                            "debug_file": "firefox.pdb",
                            "debug_id": "2B38B86A9FD04FABB58EF77C7CD654092",
                            "end_addr": "0x994000",
                            "filename": "firefox.exe",
                            "version": "24.3.0.5144"
                        },
                        {
                            "base_addr": "0x2c60000",
                            "debug_file": "kswebshield.pdb",
                            "debug_id": "056410AE957A40038EAA8984EAD6EC1A1",
                            "end_addr": "0x2d4f000",
                            "filename": "kswebshield.dll",
                            "missing_symbols": True,
                            "version": "2013.4.9.86"
                        },
                    ],
                            "sensitive": {
                        "exploitability": "low"
                    },
                    "status": "OK",
                    "system_info": {
                        "cpu_arch": "x86",
                        "cpu_count": 4,
                        "cpu_info": "GenuineIntel family 6 model 58 stepping 9",
                        "os": "Windows NT",
                        "os_ver": "6.1.7601 Service Pack 1"
                    },
                    "thread_count": 50,
                    "threads": [
                        {
                            "frame_count": 2,
                            "frames": [
                                {
                                    "file": "f:/dd/vctools/crt_bld/SELF_X86/crt/src/INTEL/memcpy.asm",
                                    "frame": 0,
                                    "function": "memcpy",
                                    "function_offset": "0x154",
                                    "line": 319,
                                    "module": "msvcr100.dll",
                                    "module_offset": "0x1fd4",
                                    "offset": "0x6ce51fd4",
                                    "trust": "context"
                                },
                                {
                                    "file": "hg:hg.mozilla.org/releases/mozilla-esr24:xpcom/string/src/nsTSubstring.cpp:d06a17a96fa2",
                                    "frame": 1,
                                    "function": "nsACString_internal::Assign(nsCSubstringTuple const &,mozilla::fallible_t const &)",
                                    "function_offset": "0xa4",
                                    "line": 416,
                                    "module": "xul.dll",
                                    "module_offset": "0xe2884",
                                    "offset": "0x63892884",
                                    "trust": "frame_pointer"
                                },
                            ]
                        },
                    ],
                },
                "last_crash": 105,
                "os_name": "Windows NT",
                "os_version": "6.1.7601 Service Pack 1",
                "pluginFilename": None,
                "pluginName": None,
                "pluginVersion": None,
                "process_type": None,
                "processor_notes": "socorro-processor1_stage_metrics_phx1_mozilla_com.24717:2012; HybridCrashProcessor",
                "product": "WaterWolf",
                "productid": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
                "reason": "EXCEPTION_ACCESS_VIOLATION_READ",
                "release_channel": "esr",
                "signature": "memcpy | nsACString_internal::Assign(nsCSubstringTuple const&, mozilla::fallible_t const&) | nsACString_internal::Assign(nsCSubstringTuple const&) | nsACString_internal::operator=(nsCSubstringTuple const&)",
                "startedDateTime": "2014-02-19 00:00:12.474004",
                "success": True,
                "topmost_filenames": "f:/dd/vctools/crt_bld/SELF_X86/crt/src/INTEL/memcpy.asm",
                "truncated": False,
                "uptime": 94,
                "url": None,
                "user_comments": None,
                "user_id": "",
                "uuid": crashid,
                "version": "24.3.0esr"
            }
            row = [crashid, json.dumps(processed_crash), date_processed]
            yield row


# the order that tables are loaded is important.
tables = [Products, ProductReleaseChannels, ProductBuildTypes,
          RawADI, ReleasesRaw, Reports, RawCrashes, UpdateChannelMap,
          ProcessedCrashes, ProductProductidMap]

# FIXME this could be built up from BaseTable's releases dict, instead
featured_versions = ('5.0a1', '4.0a2', '3.1b1', '2.1')
