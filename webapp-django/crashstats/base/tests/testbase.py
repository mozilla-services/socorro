import mock

import django.test
import django.utils.unittest

from crashstats.supersearch.models import (
    SuperSearch,
    SuperSearchFields,
    SuperSearchField,
    SuperSearchMissingFields,
)


class TestCase(django.utils.unittest.TestCase):

    def shortDescription(self):
        return None


class DjangoTestCase(django.test.TestCase):

    def setUp(self):
        super(DjangoTestCase, self).setUp()

        # These are all the classes who have an implementation
        # (e.g. a class that belongs to socorro.external.something.something)
        # They all need to be mocked.
        # NOTE! At the time of writing, these are all related to SuperSearch
        # but it's just a temporary coincidence because that's what we're
        # attacking first in
        # https://bugzilla.mozilla.org/show_bug.cgi?id=1188083
        classes_with_implementation = (
            SuperSearch,
            SuperSearchFields,
            SuperSearchField,
            SuperSearchMissingFields,
        )

        for klass in classes_with_implementation:
            klass.implementation = mock.MagicMock()
            # The class name is used by the internal caching that guards
            # for repeated calls with the same parameter.
            # If we don't do this the cache key will always have the
            # string 'MagicMock' in it no matter which class it came from.
            klass.implementation().__class__.__name__ = klass.__name__

    def shortDescription(self):
        return None
