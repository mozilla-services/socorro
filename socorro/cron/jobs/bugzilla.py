from configman import Namespace
from socorro.cron.crontabber import PostgreSQLCronApp


_URL = 'https://bugzilla.mozilla.org/buglist.cgi?query_format=advanced&short_d'
       'esc_type=allwordssubstr&short_desc=&long_desc_type=allwordssubstr&long'
       '_desc=&bug_file_loc_type=allwordssubstr&bug_file_loc=&status_whiteboar'
       'd_type=allwordssubstr&status_whiteboard=&keywords_type=allwords&keywor'
       'ds=&deadlinefrom=&deadlineto=&emailassigned_to1=1&emailtype1=substring'
       '&email1=&emailassigned_to2=1&emailreporter2=1&emailqa_contact2=1&email'
       'cc2=1&emailtype2=substring&email2=&bugidtype=include&bug_id=&votes=&ch'
       'fieldfrom=%s&chfieldto=Now&chfield=[Bug+creation]&chfield=resolution&c'
       'hfield=bug_status&chfield=short_desc&chfield=cf_crash_signature&chfiel'
       'dvalue=&cmdtype=doit&order=Importance&field0-0-0=noop&type0-0-0=noop&v'
       'alue0-0-0=&columnlist=bug_id,bug_status,resolution,short_desc,cf_crash'
       '_signature&ctype=csv'

class BugzillaCronApp(PostgreSQLCronApp):
    app_name = 'bugzilla'
    app_description = 'Bugzilla Associations'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'query',
        default=_URL,
        doc='Explanation of the option')

    required_config.add_option(
        'persistent_data_pathname',
        default='./bugzilla.pickle',
        doc='a pathname to a file system location where this script can '
            'store persistent data')

    required_config.add_option(
        'days_into_past',
        default=0,
        doc='number of days to look into the past for bugs (0 - use last '
            'run time)')

    def run(self, connection):
        # record_associations

        raise NotImplementedError
