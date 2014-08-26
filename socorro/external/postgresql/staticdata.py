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
            ['Windows 7', '6', '1']]


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
               'fkeys', 'partition_column', 'timetype']
    rows = [['reports', '1', '{id,uuid}',
             '{date_processed,hangid,"product,version",reason,signature,url}',
             '{}', 'date_processed', 'TIMESTAMPTZ'],
            ['plugins_reports', '2', '{"report_id,plugin_id"}',
             '{"report_id,date_processed"}',
             ('{"(plugin_id) REFERENCES plugins(id)","(report_id)'
              ' REFERENCES reports_WEEKNUM(id)"}'),
             'date_processed', 'TIMESTAMPTZ'],
            ['extensions', '3', '{"report_id,extension_key"}',
             '{"report_id,date_processed"}',
             '{"(report_id) REFERENCES reports_WEEKNUM(id)"}',
             'date_processed', 'TIMESTAMPTZ'],
            ['raw_crashes', '4', '{uuid}', '{}', '{}', 'date_processed',
                'TIMESTAMPTZ'],
            ['signature_summary_installations', '5',
             '{"signature_id,product_name,version_string,report_date"}',
             '{}',
             '{"(signature_id) REFERENCES signatures(signature_id)"}',
             'report_date', 'DATE'],
            ['processed_crashes', '6', '{uuid}', '{}', '{}', 'date_processed',
                'TIMESTAMPTZ']]


class Skiplist(BaseTable):
    table = 'skiplist'
    columns = ['category', 'rule']
    rows = [['ignore', 'everything'],
            ['prefix', 'SocketShutdown']]


# the order that tables are loaded is important.
tables = [OSNames, OSNameMatches, ProcessTypes, ReleaseChannels,
          ReleaseChannelMatches, UptimeLevels, WindowsVersions,
          OSVersions, ReleaseRepositories, CrontabberState,
          CrashTypes, ReportPartitionInfo, Skiplist]
