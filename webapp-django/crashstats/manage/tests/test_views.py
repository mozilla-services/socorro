import json
import datetime
import os
import urlparse

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Group, Permission
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

import mock
import pytest
from pinax.eventlog.models import Log

from crashstats.status.models import StatusMessage
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
        events_url = reverse('manage:events')
        assert events_url in response.content

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
        user = self._login()
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

        event, = Log.objects.all()
        assert event.user == user
        assert event.action == 'graphicsdevices.add'
        assert event.extra['payload'] == [data]
        assert event.extra['success'] is True

    def test_graphics_devices_csv_upload_pcidatabase_com(self):
        user = self._login()
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

        event, = Log.objects.all()
        assert event.user == user
        assert event.action == 'graphicsdevices.post'
        assert event.extra['success'] is True
        assert event.extra['database'] == 'pcidatabase.com'
        assert event.extra['no_lines'] == 7

    def test_graphics_devices_csv_upload_pci_ids(self):
        user = self._login()
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

        event, = Log.objects.all()
        assert event.user == user
        assert event.action == 'graphicsdevices.post'
        assert event.extra['success'] is True
        assert event.extra['database'] == 'pci.ids'
        assert event.extra['no_lines'] == 6

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

    def test_view_events_page(self):
        url = reverse('manage:events')
        response = self.client.get(url)
        assert response.status_code == 302
        user = self._login()

        # this page will iterate over all unique possible Log actions
        Log.objects.create(
            user=user,
            action='actionA'
        )
        Log.objects.create(
            user=user,
            action='actionB'
        )
        Log.objects.create(
            user=user,
            action='actionA'
        )
        response = self.client.get(url)
        assert response.status_code == 200
        # for the action filter drop-downs
        assert response.content.count('value="actionA"') == 1
        assert response.content.count('value="actionB"') == 1

    def test_events_data(self):
        url = reverse('manage:events_data')
        response = self.client.get(url)
        assert response.status_code == 302
        user = self._login()

        Log.objects.create(
            user=user,
            action='actionA',
            extra={'foo': True}
        )
        other_user = User.objects.create(
            username='other',
            email='other@email.com'
        )
        Log.objects.create(
            user=other_user,
            action='actionB',
            extra={'bar': False}
        )
        third_user = User.objects.create(
            username='third',
            email='third@user.com',
        )
        now = timezone.now()
        for i in range(settings.EVENTS_ADMIN_BATCH_SIZE * 2):
            Log.objects.create(
                user=third_user,
                action='actionX',
                timestamp=now - datetime.timedelta(
                    seconds=i + 1
                )
            )

        response = self.client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['count'] == 2 + settings.EVENTS_ADMIN_BATCH_SIZE * 2
        # the most recent should be "actionB"
        assert len(data['events']) == settings.EVENTS_ADMIN_BATCH_SIZE
        first = data['events'][0]
        assert first['action'] == 'actionB'
        assert first['extra'] == {'bar': False}

        # try to go to another page
        response = self.client.get(url, {'page': 'xxx'})
        assert response.status_code == 400
        response = self.client.get(url, {'page': '0'})
        assert response.status_code == 400

        response = self.client.get(url, {'page': '2'})
        assert response.status_code == 200
        data = json.loads(response.content)
        first = data['events'][0]
        # we should now be on one of the actionX events
        assert first['action'] == 'actionX'

        # we can filter by user
        response = self.client.get(url, {'user': 'other'})
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['count'] == 1

        # we can filter by action
        response = self.client.get(url, {'action': 'actionX'})
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['count'] == settings.EVENTS_ADMIN_BATCH_SIZE * 2

    def test_events_data_urls(self):
        """some logged events have a URL associated with them"""
        user = self._login()

        Log.objects.create(
            user=user,
            action='user.edit',
            extra={'id': user.id}
        )

        group = Group.objects.create(name='Wackos')
        Log.objects.create(
            user=user,
            action='group.add',
            extra={'id': group.id}
        )
        Log.objects.create(
            user=user,
            action='group.edit',
            extra={'id': group.id}
        )
        url = reverse('manage:events_data')
        response = self.client.get(url)
        data = json.loads(response.content)
        assert data['count'] == 3
        three, two, one = data['events']
        assert one['url'] == reverse('admin:auth_user_change', args=(user.id,))
        assert two['url'] == reverse('admin:auth_group_change', args=(group.id,))
        assert three['url'] == reverse('admin:auth_group_change', args=(group.id,))

    def test_status_message(self):
        url = reverse('manage:status_message')

        # Test while logged out.
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200

        # expects some severity options to be available as dropdowns
        expected = '<option value="%s">%s</option>' % (
            'critical',
            'Critical'
        )
        assert expected in response.content

    def test_create_status_message(self):
        url = reverse('manage:status_message')

        # Test while logged out.
        response = self.client.post(url)
        assert response.status_code == 302

        user = self._login()
        response = self.client.post(url)
        assert response.status_code == 200
        assert 'This field is required' in response.content

        response = self.client.post(url, {
            'message': 'Foo',
            'severity': 'critical'
        })
        assert response.status_code == 302

        event, = Log.objects.all()

        assert event.user == user
        assert event.action == 'status_message.create'
        assert event.extra['severity'] == 'critical'

    def test_disable_status_message(self):
        url = reverse('manage:status_message_disable', args=('99999',))
        response = self.client.get(url)
        assert response.status_code == 302

        user = self._login()
        response = self.client.get(url)
        assert response.status_code == 405
        response = self.client.post(url)
        assert response.status_code == 404

        status = StatusMessage.objects.create(
            message='foo',
            severity='critical',
        )
        url = reverse('manage:status_message_disable', args=(status.id,))

        response = self.client.post(url)
        assert response.status_code == 302  # redirect on success

        # Verify there is no enabled statuses anymore.
        assert not StatusMessage.objects.filter(enabled=True)

        event, = Log.objects.all()

        assert event.user == user
        assert event.action == 'status_message.disable'

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

    def test_reprocessing(self):
        url = reverse('manage:reprocessing')
        response = self.client.get(url)
        assert response.status_code == 302

        good_crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
        bad_crash_id = '00000000-0000-0000-0000-000000020611'

        def mocked_reprocess(crash_ids):
            assert isinstance(crash_ids, list)
            if crash_ids == [good_crash_id]:
                return True
            elif crash_ids == [bad_crash_id]:
                return
            raise NotImplementedError(crash_ids)

        models.Reprocessing.implementation().reprocess = mocked_reprocess

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200

        response = self.client.post(
            url,
            {'crash_id': 'junk'},
        )
        assert response.status_code == 200
        assert 'Does not appear to be a valid crash ID' in response.content

        response = self.client.post(
            url,
            {'crash_id': good_crash_id},
        )
        assert response.status_code == 302
        self.assertRedirects(
            response,
            url + '?crash_id=' + good_crash_id
        )

        response = self.client.post(
            url,
            {'crash_id': bad_crash_id},
        )
        assert response.status_code == 302
        self.assertRedirects(
            response,
            url  # note lack of `?crash_id=...`
        )
