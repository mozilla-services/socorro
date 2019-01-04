import csv
import datetime

import six

from django.conf import settings
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.encoding import smart_text

from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.graphics.views import GRAPHICS_REPORT_HEADER
from crashstats.supersearch.models import SuperSearch


class TestViews(BaseTestViews):
    def test_graphics_report(self):

        def mocked_supersearch_get(**params):
            assert params['product'] == [settings.DEFAULT_PRODUCT]
            hits = [
                {
                    'signature': 'my signature',
                    'date': '2015-10-08T23:22:21.1234 +00:00',
                    'cpu_name': 'arm',
                    'cpu_info': 'ARMv7 ARM',
                },
                {
                    'signature': 'other signature',
                    'date': '2015-10-08T13:12:11.1123 +00:00',
                    'cpu_info': 'something',
                    # note! no cpu_name
                },
            ]
            # Value for each of these needs to be in there
            # supplement missing ones from the fixtures we intend to return.
            for hit in hits:
                for head in GRAPHICS_REPORT_HEADER:
                    if head not in hit:
                        hit[head] = None
            return {
                'hits': hits,
                'total': 2
            }

        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        url = reverse('graphics:report')

        # viewing this report requires that you're signed in
        response = self.client.get(url)
        assert response.status_code == 403

        # But being signed in isn't good enough, you need the right
        # permissions too.
        user = self._login()
        response = self.client.get(url)
        assert response.status_code == 403

        # Add the user to the Hackers group which has run_long_queries
        # permission
        group = Group.objects.get(name='Hackers')
        user.groups.add(group)

        # But even with the right permissions you still need to
        # provide the right minimal parameters.
        response = self.client.get(url)
        assert response.status_code == 400

        # Let's finally get it right. Permission AND the date parameter.
        data = {'date': datetime.datetime.utcnow().date()}
        response = self.client.get(url, data)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert response['Content-Length'] == str(len(response.content))

        # the response content should be parseable
        text = smart_text(response.content)
        inp = six.StringIO(text)

        reader = csv.reader(inp, delimiter='\t')
        lines = list(reader)
        assert len(lines) == 3
        header = lines[0]
        assert header == list(GRAPHICS_REPORT_HEADER)
        first = lines[1]
        assert first[GRAPHICS_REPORT_HEADER.index('signature')] == 'my signature'
        assert first[GRAPHICS_REPORT_HEADER.index('date_processed')] == '201510082322'

    def test_graphics_report_not_available_via_regular_web_api(self):
        # check that the model isn't available in the API documentation
        api_url = reverse('api:model_wrapper', args=('GraphicsReport',))
        response = self.client.get(reverse('api:documentation'))
        assert response.status_code == 200
        assert api_url not in smart_text(response.content)
