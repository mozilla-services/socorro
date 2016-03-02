import json

from functools import partial

from configman import Namespace, class_converter
from socorrolib.app.socorro_app import App, main


#==============================================================================
class FetchApp(App):

    #--------------------------------------------------------------------------
    required_config = Namespace()
    required_config.add_option(
        name='command',
        doc='what data to fetch (%s)',
        default='processed_crash',
        is_argument=True,
    )
    required_config.add_option(
        name='crash_id',
        doc='the crash_id',
        default='',
        is_argument=True,
    )
    required_config.add_option(
        name='dump_name',
        doc='the name of the dump required',
        default='',
        is_argument=True,
    )
    required_config.add_option(
        name='crashstorage_class',
        doc='the crash storage system class',
        default='socorro.external.boto.crashstorage.BotoS3CrashStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    app_name = "FetchApp"
    app_version = "1.0"
    app_description = 'get data from socorro'

    #--------------------------------------------------------------------------
    @staticmethod
    def get_application_defaults():
        """since this app is more of an interactive app than the others, the
        logging of config information is rather disruptive.  Override the
        default logging level to one that is less annoying."""
        return {
            'logging.stderr_error_logging_level': 50
        }

    #--------------------------------------------------------------------------
    def method_not_found(self):
        return "we're sorry, but %s is not a command" % self.config.command

    #--------------------------------------------------------------------------
    def raw_crash_command(self,):
        return json.dumps(
            self.crash_store.get_raw_crash(self.config.crash_id),
            sort_keys=True,
            indent=4,
            separators=(',', ': '),
        )

    #--------------------------------------------------------------------------
    def processed_crash_command(self):
        return json.dumps(
            self.crash_store.get_unredacted_processed(self.config.crash_id),
            sort_keys=True,
            indent=4,
            separators=(',', ': '),
        )

    #--------------------------------------------------------------------------
    def raw_dump_command(self):
        return self.crash_store.get_raw_dump(
            self.config.crash_id,
            self.config.dump_name
        )

    #--------------------------------------------------------------------------
    def raw_dumps_as_files_command(self):
        return self.crash_store.get_raw_dumps_as_files(
            self.config.crash_id
        )

    #--------------------------------------------------------------------------
    def find_method(self, a_method_name):
        try:
            return getattr(self, a_method_name + '_command')
        except AttributeError:
            return partial(self.method_not_found, a_method_name)

    #--------------------------------------------------------------------------
    def main(self):
        self.crash_store = self.config.crashstorage_class(self.config)
        command = self.find_method(self.config.command)
        result = command()
        if result is not None:
            print result


commands = []
for a_symbol in dir(FetchApp):
    if a_symbol.endswith('_command'):
        commands.append(a_symbol.replace('_command', ''))

FetchApp.required_config.command.doc = (
    FetchApp.required_config.command.doc % ', '.join(commands)
)



if __name__ == '__main__':
    main(FetchApp)
