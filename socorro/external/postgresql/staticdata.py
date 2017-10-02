"""
Static data for Socorro - basic information that Socorro expects to be
present in the database in order to function correctly.
"""


class BaseTable(object):
    def generate_rows(self):
        return iter(self.rows)


class OSNames(BaseTable):
    table = 'os_names'
    columns = ['os_name', 'os_short_name']
    rows = [['Windows', 'win'],
            ['Mac OS X', 'mac'],
            ['Linux', 'lin'],
            ['Unknown', 'unknown']]


class OSNameMatches(BaseTable):
    table = 'os_name_matches'
    columns = ['os_name', 'match_string']
    rows = [['Windows', 'Windows%'],
            ['Mac OS X', 'Mac%'],
            ['Mac OS X', 'Darwin%'],
            ['Linux', 'Linux%']]


class ProcessTypes(BaseTable):
    table = 'process_types'
    columns = ['process_type']
    rows = [['browser'],
            ['plugin'],
            ['content']]


class ReleaseChannels(BaseTable):
    table = 'release_channels'
    columns = ['release_channel', 'sort']
    rows = [['Nightly', '1'],
            ['Aurora', '2'],
            ['Beta', '3'],
            ['Release', '4'],
            ['ESR', '5']]


class ReleaseChannelMatches(BaseTable):
    table = 'release_channel_matches'
    columns = ['release_channel', 'match_string']
    rows = [['Release', 'release'],
            ['Release', 'default'],
            ['Beta', 'beta'],
            ['Aurora', 'aurora'],
            ['Nightly', 'nightly%']]


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
            ['Windows 7', '6', '1'],
            ['Windows 8', '6', '2'],
            ['Windows 8.1', '6', '3'],
            ['Windows 10', '10', '0']]


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


class ReleaseRepositories(BaseTable):
    table = 'release_repositories'
    columns = ['repository']
    rows = [
        ['mozilla-central'],
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
        ['b2g-release'],
        ['mozilla-aurora-android-xul'],
        ['mozilla-central-android-xul'],
        ['comm-aurora'],
        ['mozilla-central-android-api-11'],
        ['mozilla-aurora-android-api-11'],
        ['mozilla-central-android-api-15'],
        ['mozilla-aurora-android-api-15'],
        ['mozilla-beta-android-api-15'],
        ['mozilla-release-android-api-15'],
        ['mozilla-central-android-api-16'],
        ['mozilla-esr38'],
        ['mozilla-esr45'],
        ['comm-esr38'],
        ['comm-esr45'],
        ['comm-beta'],
        ['mozilla-esr52'],
        ['comm-esr52'],
    ]


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
    columns = [
        'table_name', 'build_order', 'keys', 'indexes', 'fkeys', 'partition_column', 'timetype'
    ]
    rows = [
        (
            'reports',
            '1',
            '{id,uuid}',
            '{date_processed,hangid,"product,version",reason,signature,url}',
            '{}',
            'date_processed',
            'TIMESTAMPTZ'
        ),
        (
            'extensions',
            '3',
            '{"report_id,extension_key"}',
            '{"report_id,date_processed"}',
            '{"(report_id) REFERENCES reports_WEEKNUM(id)"}',
            'date_processed',
            'TIMESTAMPTZ'
        ),
        (
            'raw_crashes',
            '4',
            '{uuid}',
            '{date_processed}',
            '{}',
            'date_processed',
            'TIMESTAMPTZ'
        ),
        (
            'processed_crashes',
            '12',
            '{uuid}',
            '{date_processed}',
            '{}',
            'date_processed',
            'TIMESTAMPTZ'
        ),
        (
            'missing_symbols',
            '13',
            '{}',
            '{}',
            '{}',
            'date_processed',
            'DATE'
        ),
    ]


class Products(BaseTable):
    table = 'products'
    columns = [
        'product_name', 'sort', 'rapid_release_version', 'release_name', 'rapid_beta_version'
    ]
    rows = [
        ['Fennec', '3', '5.0', 'mobile', '999.0'],
        ['Thunderbird', '2', '6.0', 'thunderbird', '999.0'],
        ['Firefox', '1', '5.0', 'firefox', '23.0'],
        ['SeaMonkey', '6', '2.3', 'seamonkey', '999.0'],
        ['FennecAndroid', '4', '5.0', '**SPECIAL**', '999.0'],
    ]


class ProductBuildTypes(BaseTable):
    table = 'product_build_types'
    columns = [
        'product_name', 'build_type', 'throttle'
    ]
    rows = [
        ['Firefox', 'esr', '1.0',],
        ['Firefox', 'aurora', '1.0'],
        ['Firefox', 'beta', '1.0'],
        ['Firefox', 'release', '0.1'],
        ['Firefox', 'nightly', '1.0'],
    ]


# DEPRECATED
class ProductReleaseChannels(BaseTable):
    table = 'product_release_channels'
    columns = [
        'product_name', 'release_channel', 'throttle'
    ]
    rows = [
        ['Firefox', 'ESR', '1.0'],
        ['Firefox', 'Aurora', '1.0'],
        ['Firefox', 'Beta', '1.0'],
        ['Firefox', 'Release', '0.1'],
        ['Firefox', 'Nightly', '1.0'],
    ]


class SpecialProductPlatforms(BaseTable):
    table = 'special_product_platforms'
    columns = [
        'platform', 'repository', 'release_channel', 'release_name', 'product_name', 'min_version'
    ]
    rows = [
        ['android', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '10.0'],
        ['android', 'mozilla-release', 'beta', 'mobile', 'FennecAndroid', '10.0'],
        ['android', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '10.0'],
        ['android-arm', 'mozilla-central-android', 'nightly', 'mobile', 'FennecAndroid', '10.0'],
        ['android-arm', 'mozilla-central-android', 'aurora', 'mobile', 'FennecAndroid', '10.0'],
        ['android-arm', 'mozilla-aurora-android', 'aurora', 'mobile', 'FennecAndroid', '10.0'],
        ['android-arm', 'mozilla-central-android-api-11', 'nightly', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-aurora-android-api-11', 'aurora', 'mobile', 'FennecAndroid', '37.0'],
        ['android-x86', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '37.0'],
        ['android-api-9', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '37.0'],
        ['android-api-11', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '37.0'],
        ['android-x86', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '37.0'],
        ['android-api-9', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '37.0'],
        ['android-api-11', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-central-android-api-15', 'nightly', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-aurora-android-api-15', 'aurora', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-beta-android-api-15', 'beta', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-release-android-api-15', 'release', 'mobile', 'FennecAndroid', '37.0'],

        # FennecAndroid 56+
        ['android-arm', 'mozilla-central-android-api-16', 'nightly', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-beta-android-api-16', 'aurora', 'mobile', 'FennecAndroid', '37.0'],
        ['android-arm', 'mozilla-release-android-api-16', 'aurora', 'mobile', 'FennecAndroid', '37.0'],
    ]


# the order that tables are loaded is important.
tables = [OSNames, OSNameMatches, ProcessTypes, ReleaseChannels,
          ReleaseChannelMatches, UptimeLevels, WindowsVersions,
          OSVersions, ReleaseRepositories,
          CrashTypes, ReportPartitionInfo,
          Products, ProductBuildTypes, ProductReleaseChannels, SpecialProductPlatforms]
