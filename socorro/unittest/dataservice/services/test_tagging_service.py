from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises
from mock import Mock

from configman.dotdict import DotDict

from socorro.unittest.testbase import TestCase

from socorro.dataservice.services.tagging_service import TaggingService
from socorro.external.crashstorage_base import CrashIDNotFound

class TestTaggingService(TestCase):

    def create_config(self):
        config = DotDict()
        config.logger = Mock()
        config['source.crashstorage_class'] = Mock()
        config['destination.crashstorage_class'] = Mock()
        return config

    def test_post_everything_we_expected(self):
        config = self.create_config()

        # tested call
        ts = TaggingService(config)

        eq_(ts.source, config.source.crashstorage_class.return_value)
        eq_(ts.destination, config.destination.crashstorage_class.return_value)

        ts.source.get_unredacted_processed.return_value = {}

        # the tested call
        ts.post(crash_id='13', tag='thirteen')

        ts.source.get_unredacted_processed.assert_called_with('13')
        ts.destination.save_processed.assert_called_with(
            {'tags': {'thirteen': False }}
        )

    def test_post_tags_already_exist(self):
        config = self.create_config()

        ts = TaggingService(config)
        ts.source.get_unredacted_processed.return_value = {
            'tags': {'blue': False}
        }

        # the tested call
        ts.post(crash_id='13', tag='thirteen')

        ts.source.get_unredacted_processed.assert_called_with('13')
        ts.destination.save_processed.assert_called_with(
            {
                'tags': {
                    'thirteen': False,
                    'blue': False,
                }
            }
        )

    def test_post_missing_parameter(self):
        config = self.create_config()

        ts = TaggingService(config)
        ts.source.get_unredacted_processed.return_value = {}

        # the tested call
        self.assertRaises(
            TypeError,
            ts.post,
            tag='thirteen'
        )


    def test_post_processed_crash_missing(self):
        config = self.create_config()

        ts = TaggingService(config)
        ts.source.get_unredacted_processed.side_effect = CrashIDNotFound

        # the tested call
        self.assertRaises(
            CrashIDNotFound,
            ts.post,
            crash_id='13',
            tag='thirteen'
        )




