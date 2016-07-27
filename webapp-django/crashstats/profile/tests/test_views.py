import pyquery
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from crashstats.crashstats.management import PERMISSIONS
from crashstats.supersearch.models import SuperSearchUnredacted
from crashstats.crashstats.tests.test_views import BaseTestViews


class TestViews(BaseTestViews):

    def test_profile(self):

        def mocked_supersearch_get(**params):
            assert '_columns' in params
            assert '_sort' in params
            assert 'email' in params
            assert params['email'] == ['test@mozilla.com']

            results = {
                'hits': [
                    {
                        'uuid': '1234abcd-ef56-7890-ab12-abcdef130802',
                        'date': '2000-01-02T00:00:00'
                    },
                    {
                        'uuid': '1234abcd-ef56-7890-ab12-abcdef130801',
                        'date': '2000-01-01T00:00:00'
                    },
                ],
                'total': 2
            }
            return results

        def mocked_supersearch_get_no_data(**params):
            assert 'email' in params
            assert params['email'] == ['test@mozilla.com']

            return {
                'hits': [],
                'total': 0
            }

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        url = reverse('profile:profile')

        # Test that the user must be signed in.
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )

        # Now log in for the remaining tests.
        user = self._login()

        # Test with results and check email is there.
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('1234abcd-ef56-7890-ab12-abcdef130801' in response.content)
        ok_('1234abcd-ef56-7890-ab12-abcdef130802' in response.content)
        ok_('test@mozilla.com' in response.content)

        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get_no_data
        )

        # Test with no results.
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('test@mozilla.com' in response.content)
        ok_('no crash report' in response.content)

        # Make some permissions.
        self._create_group_with_permission(
            'view_pii', 'Group A'
        )
        group_b = self._create_group_with_permission(
            'view_exploitability', 'Group B'
        )
        user.groups.add(group_b)
        assert not user.has_perm('crashstats.view_pii')
        assert user.has_perm('crashstats.view_exploitability')

        # Test permissions.
        response = self.client.get(url)
        ok_(PERMISSIONS['view_pii'] in response.content)
        ok_(PERMISSIONS['view_exploitability'] in response.content)
        doc = pyquery.PyQuery(response.content)
        for row in doc('table.permissions tbody tr'):
            cells = []
            for td in doc('td', row):
                cells.append(td.text.strip())
            if cells[0] == PERMISSIONS['view_pii']:
                eq_(cells[1], 'No')
            elif cells[0] == PERMISSIONS['view_exploitability']:
                eq_(cells[1], 'Yes!')

        # If the user ceases to be active, this page should redirect instead
        user.is_active = False
        user.save()
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )

    def test_homepage_profile_footer(self):
        """This test isn't specifically for the profile page, because
        it ultimately tests the crashstats_base.html template. But
        that template has a link to the profile page."""
        url = reverse('home:home', args=('WaterWolf',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        profile_url = reverse('profile:profile')
        ok_(profile_url not in response.content)

        # Render again when signed in
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(profile_url in response.content)

        # Render again when no longer an active user
        user.is_active = False
        user.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(profile_url not in response.content)
