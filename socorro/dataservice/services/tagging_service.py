# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.lib.external_common import parse_arguments

from configman import RequiredConfig, Namespace, class_converter

#==============================================================================
class TaggingService(RequiredConfig):

    # Necessary for use with socorro.webapi.servers.WebServerBase
    uri = r'/tag/(.*)'

    filters = [
        ("crash_id", None, ["str",]),
        ("tag", None, ["str",]),
    ]

    required_config = Namespace()
    required_config.source = Namespace()
    required_config.source.add_option(
        'crashstorage_class',
        doc='the source storage class',
        default=None,
        from_string_converter=class_converter
    )
    required_config.destination = Namespace()
    required_config.destination.add_option(
        'crashstorage_class',
        doc='the destination storage class',
        default=None,
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check=None):
        self.config = config
        try:
            self.source = self.config.source.crashstorage_class(
              self.config.source,
              quit_check_callback=quit_check
            )
        except Exception:
            self.config.logger.critical(
              'Error in creating crash source',
              exc_info=True
            )
            raise
        try:
            self.destination = self.config.destination.crashstorage_class(
              self.config.destination,
              quit_check_callback=quit_check
            )
        except Exception:
            self.config.logger.critical(
              'Error in creating crash destination',
              exc_info=True
            )
            raise

    #--------------------------------------------------------------------------
    def post(self, crash_id, tag):
        try:
            processed_crash = self.source.get_unredacted_processed(crash_id)
            tags = processed_crash.setdefault('tags', {})
            tags[tag] = False  # when processed this tag becomes True
            self.destination.save_processed(processed_crash)
        except Exception, x:
            self.config.logger.error(str(x))
            raise



