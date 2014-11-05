import mock
from nose.tools import eq_, ok_, assert_raises

from django.core.urlresolvers import reverse

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats.models import BadStatusCodeError
from crashstats.crashstats.tests.test_models import Response


class TestPropagate400Errors(DjangoTestCase):

    @mock.patch('requests.get')
    def test_propagate_400_error(self, rget):
        # first we need to do something that catches data from the
        # models and we'll pretend the middleware returned a 400 Bad Request

        def mocked_get(**options):
            return Response('Naughty boy!', status_code=400)

        rget.side_effect = mocked_get

        url = reverse('crashstats:home', args=('WaterWolf',))
        response = self.client.get(url)
        eq_(response.status_code, 400)
        ok_('Naughty boy!' in response.content)

    @mock.patch('requests.get')
    def test_propagate_400_error_disabled(self, rget):

        def mocked_get(**options):
            return Response('Naughty boy!', status_code=400)

        rget.side_effect = mocked_get

        with self.settings(PROPAGATE_MIDDLEWARE_400_ERRORS=False):
            url = reverse('crashstats:home', args=('WaterWolf',))
            assert_raises(BadStatusCodeError, self.client.get, url)
