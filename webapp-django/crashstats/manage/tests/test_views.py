import json
import os
import urlparse

from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

import mock
import pytest

from crashstats.supersearch.models import (
    SuperSearchFields,
    SuperSearchMissingFields,
)
from crashstats.crashstats import models
from crashstats.crashstats.tests.test_views import (
    BaseTestViews,
)


class TestViews(BaseTestViews):

    def setUp(self):
        super(TestViews, self).setUp()

        def mocked_product_versions(**params):
            hits = [
                {
                    'is_featured': True,
                    'throttle': 1.0,
                    'end_date': 'string',
                    'start_date': 'integer',
                    'build_type': 'string',
                    'product': 'WaterWolf',
                    'version': '19.0',
                    'has_builds': True
                }
            ]
            return {
                'hits': hits,
                'total': len(hits),
            }

        models.ProductVersions.implementation().get.side_effect = (
            mocked_product_versions
        )
        # prime the cache
        models.ProductVersions().get(active=True)

    def _login(self, is_superuser=True):
        user = super(TestViews, self)._login(
            username='kairo',
            email='kai@ro.com',
        )
        user.is_superuser = is_superuser
        user.save()
        return user

    def _create_permission(self, name='Mess Around', codename='mess_around'):
        ct, __ = ContentType.objects.get_or_create(
            model='',
            app_label='crashstats',
        )
        return Permission.objects.create(
            name=name,
            codename=codename,
            content_type=ct
        )

    def test_home_page_not_signed_in(self):
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        assert response.status_code == 302
        # because the home also redirects to the first product page
        # we can't use assertRedirects
        assert urlparse.urlparse(response['location']).path == settings.LOGIN_URL

        # if you're logged in, but not a superuser you'll get thrown
        # back on the home page with a message
        self._login(is_superuser=False)
        response = self.client.get(home_url, follow=True)
        assert response.status_code == 200
        msg = (
            'You are signed in but you do not have sufficient permissions '
            'to reach the resource you requested.'
        )
        assert msg in response.content

    def test_home_page_signed_in(self):
        user = self._login()
        # at the moment it just redirects
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        assert response.status_code == 200

        # certain links on that page
        fields_missing_url = reverse('manage:supersearch_fields_missing')
        assert fields_missing_url in response.content
        graphics_url = reverse('manage:graphics_devices')
        assert graphics_url in response.content

        user.is_active = False
        user.save()
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        assert response.status_code == 302

    def test_analyze_model_fetches(self):
        self._login()
        url = reverse('manage:analyze_model_fetches')
        response = self.client.get(url)
        assert response.status_code == 200

    def test_render_graphics_devices_page(self):
        url = reverse('manage:graphics_devices')
        response = self.client.get(url)
        assert response.status_code == 302
        self._login()
        response = self.client.get(url)
        assert response.status_code == 200

    def test_graphics_devices_lookup(self):
        self._login()
        url = reverse('manage:graphics_devices_lookup')

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

        models.GraphicsDevices.implementation().get.side_effect = (
            mocked_get
        )

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
        url = reverse('manage:graphics_devices')

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

        models.GraphicsDevices.implementation().post.side_effect = (
            mocked_post
        )

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
        url = reverse('manage:graphics_devices')

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

        models.GraphicsDevices.implementation().post.side_effect = (
            mocked_post
        )

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
        url = reverse('manage:graphics_devices')

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

        models.GraphicsDevices.implementation().post.side_effect = (
            mocked_post
        )

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

    def test_supersearch_fields_missing(self):
        self._login()
        url = reverse('manage:supersearch_fields_missing')

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

    def test_crash_me_now(self):
        url = reverse('manage:crash_me_now')
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200

        with pytest.raises(NameError):
            self.client.post(
                url,
                {
                    'exception_type': 'NameError',
                    'exception_value': 'Crash!'
                }
            )

    def test_site_status(self):
        """Basic test to make sure the page loads and has appropriate access"""
        url = reverse('manage:site_status')
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200
