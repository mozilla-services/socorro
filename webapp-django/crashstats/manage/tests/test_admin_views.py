import mock
import pytest

from django.core.urlresolvers import reverse

from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.supersearch.models import (
    SuperSearchFields,
    SuperSearchMissingFields,
)


class SiteAdminTestViews(BaseTestViews):
    def _login(self, is_superuser=True):
        user = super(SiteAdminTestViews, self)._login(
            username='lonnen',
            email='lonnen@example.com',
        )
        user.is_superuser = is_superuser
        user.is_staff = is_superuser
        user.save()
        return user


class TestCrashMeNow(SiteAdminTestViews):
    def test_view(self):
        url = reverse('siteadmin:crash_me_now')
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        with pytest.raises(ZeroDivisionError):
            self.client.get(url)


class TestSiteStatus(SiteAdminTestViews):
    def test_page_load(self):
        """Basic test to make sure the page loads at all"""
        url = reverse('siteadmin:site_status')
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200


class TestAnalyzeModelFetches(SiteAdminTestViews):
    def test_analyze_model_fetches(self):
        """Basic test to make sure the page loads at all"""
        url = reverse('siteadmin:analyze_model_fetches')
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200


class TestSuperSearchFieldsMissing(SiteAdminTestViews):
    def test_supersearch_fields_missing(self):
        url = reverse('siteadmin:supersearch_fields_missing')
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()

        def mocked_supersearchfields(**params):
            return {
                'product': {
                    'name': 'product',
                    'namespace': 'processed_crash',
                    'in_database_name': 'product',
                    'query_type': 'enum',
                    'form_field_choices': None,
                    'permissions_needed': [],
                    'default_value': None,
                    'is_exposed': True,
                    'is_returned': True,
                    'is_mandatory': False,
                }
            }

        def mocked_supersearchfields_get_missing_fields(**params):
            return {
                'hits': [
                    'field_a',
                    'namespace1.field_b',
                    'namespace2.subspace1.field_c',
                ],
                'total': 3
            }

        supersearchfields_mock_get = mock.Mock()
        supersearchfields_mock_get.side_effect = mocked_supersearchfields
        SuperSearchFields.get = supersearchfields_mock_get

        SuperSearchMissingFields.implementation().get.side_effect = (
            mocked_supersearchfields_get_missing_fields
        )

        response = self.client.get(url)
        assert response.status_code == 200
        assert 'field_a' in response.content
        assert 'namespace1.field_b' in response.content
        assert 'namespace2.subspace1.field_c' in response.content
