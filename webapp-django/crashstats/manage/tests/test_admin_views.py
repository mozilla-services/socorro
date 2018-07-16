import json
import os

import mock
import pytest

from django.core.urlresolvers import reverse

from crashstats.crashstats.models import GraphicsDevices
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


class TestGraphicsDevices(SiteAdminTestViews):
    def test_render_graphics_devices_page(self):
        url = reverse('siteadmin:graphics_devices')
        response = self.client.get(url)
        assert response.status_code == 302
        self._login()
        response = self.client.get(url)
        assert response.status_code == 200

    def test_graphics_devices_lookup(self):
        self._login()
        url = reverse('siteadmin:graphics_devices_lookup')

        def mocked_get(**params):
            if (
                'adapter_hex' in params and
                params['adapter_hex'] == 'xyz123' and
                'vendor_hex' in params and
                params['vendor_hex'] == 'abc123'
            ):
                return {
                    "hits": [
                        {
                            "vendor_hex": "abc123",
                            "adapter_hex": "xyz123",
                            "vendor_name": "Logictech",
                            "adapter_name": "Webcamera"
                        }
                    ],
                    "total": 1
                }
            raise NotImplementedError(url)

        GraphicsDevices.implementation().get.side_effect = mocked_get

        response = self.client.get(url)
        assert response.status_code == 400

        response = self.client.get(url, {
            'vendor_hex': 'abc123',
            'adapter_hex': 'xyz123',
        })
        assert response.status_code == 200
        content = json.loads(response.content)
        assert content['total'] == 1
        expected = {
            'vendor_hex': 'abc123',
            'adapter_hex': 'xyz123',
            'vendor_name': 'Logictech',
            'adapter_name': 'Webcamera'
        }
        assert content['hits'][0] == expected

    def test_graphics_devices_edit(self):
        self._login()
        url = reverse('siteadmin:graphics_devices')

        def mocked_post(**payload):
            data = payload['data']
            expected = {
                'vendor_hex': 'abc123',
                'adapter_hex': 'xyz123',
                'vendor_name': 'Logictech',
                'adapter_name': 'Webcamera'
            }
            assert data[0] == expected
            return True

        GraphicsDevices.implementation().post.side_effect = mocked_post

        data = {
            'vendor_hex': 'abc123',
            'adapter_hex': 'xyz123',
            'vendor_name': 'Logictech',
            'adapter_name': 'Webcamera'
        }
        response = self.client.post(url, data)
        assert response.status_code == 302
        assert url in response['location']

    def test_graphics_devices_csv_upload_pcidatabase_com(self):
        self._login()
        url = reverse('siteadmin:graphics_devices')

        def mocked_post(**payload):
            data = payload['data']
            expected = {
                'vendor_hex': '0x0033',
                'adapter_hex': '0x002f',
                'vendor_name': 'Paradyne Corp.',
                'adapter_name': '.43 ieee 1394 controller'
            }
            assert data[0] == expected
            assert len(data) == 7
            return True

        GraphicsDevices.implementation().post.side_effect = mocked_post

        sample_file = os.path.join(
            os.path.dirname(__file__),
            'sample-graphics.csv'
        )
        with open(sample_file) as fp:
            response = self.client.post(url, {
                'file': fp,
                'database': 'pcidatabase.com',
            })
            assert response.status_code == 302
            assert url in response['location']

    def test_graphics_devices_csv_upload_pci_ids(self):
        self._login()
        url = reverse('siteadmin:graphics_devices')

        def mocked_post(**payload):
            data = payload['data']
            expected = {
                'vendor_hex': '0x0010',
                'adapter_hex': '0x8139',
                'vendor_name': 'Allied Telesis, Inc',
                'adapter_name': 'AT-2500TX V3 Ethernet'
            }
            assert data[0] == expected
            assert len(data) == 6
            return True

        GraphicsDevices.implementation().post.side_effect = mocked_post

        sample_file = os.path.join(
            os.path.dirname(__file__),
            'sample-pci.ids'
        )
        with open(sample_file) as fp:
            response = self.client.post(url, {
                'file': fp,
                'database': 'pci.ids',
            })
            assert response.status_code == 302
            assert url in response['location']


class TestDebugView(SiteAdminTestViews):
    def test_view_loads(self):
        """Tests that the page loads--doesn't verify any information"""
        url = reverse('siteadmin:debug_view')
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        self.client.get(url)
