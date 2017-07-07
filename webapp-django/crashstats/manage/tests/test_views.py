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
from nose.tools import eq_, ok_, assert_raises
from eventlog.models import Log

from crashstats.status.models import StatusMessage
from crashstats.symbols.models import SymbolsUpload
from crashstats.tokens.models import Token
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
        eq_(
            urlparse.urlparse(response['location']).path,
            settings.LOGIN_URL
        )

        # if you're logged in, but not a superuser you'll get thrown
        # back on the home page with a message
        self._login(is_superuser=False)
        response = self.client.get(home_url, follow=True)
        assert response.status_code == 200
        ok_(
            'You are signed in but you do not have sufficient permissions '
            'to reach the resource you requested.' in response.content
        )

    def test_home_page_signed_in(self):
        user = self._login()
        # at the moment it just redirects
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        eq_(response.status_code, 200)

        # certain links on that page
        fields_url = reverse('manage:supersearch_fields')
        ok_(fields_url in response.content)
        users_url = reverse('manage:users')
        ok_(users_url in response.content)
        products_url = reverse('manage:products')
        ok_(products_url in response.content)
        releases_url = reverse('manage:releases')
        ok_(releases_url in response.content)

        user.is_active = False
        user.save()
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        eq_(response.status_code, 302)

    def test_users_page(self):
        url = reverse('manage:users')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        Group.objects.create(name='Wackos')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Wackos' in response.content)

    def test_users_data(self):
        url = reverse('manage:users_data')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 1)
        eq_(data['users'][0]['email'], user.email)
        eq_(data['users'][0]['id'], user.pk)
        eq_(data['users'][0]['is_superuser'], True)
        eq_(data['users'][0]['is_active'], True)
        eq_(data['users'][0]['groups'], [])

        austrians = Group.objects.create(name='Austrians')
        user.groups.add(austrians)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        groups = data['users'][0]['groups']
        group = groups[0]
        eq_(group['name'], 'Austrians')
        eq_(group['id'], austrians.pk)

    def test_users_data_pagination(self):
        url = reverse('manage:users_data')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        user = self._login()
        user.last_login -= datetime.timedelta(days=365)
        user.save()
        now = timezone.now()
        for i in range(1, 101):  # 100 times, 1-100
            User.objects.create(
                username='user%03d' % i,
                email='user%03d@mozilla.com' % i,
                last_login=now - datetime.timedelta(days=i)
            )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 101)
        # because it's sorted by last_login
        eq_(data['users'][0]['email'], 'user001@mozilla.com')
        eq_(len(data['users']), settings.USERS_ADMIN_BATCH_SIZE)
        eq_(data['page'], 1)
        eq_(data['batch_size'], settings.USERS_ADMIN_BATCH_SIZE)

        # let's go to page 2
        response = self.client.get(url, {'page': 2})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 101)
        # because it's sorted by last_login
        eq_(data['users'][0]['email'], 'user011@mozilla.com')
        eq_(len(data['users']), settings.USERS_ADMIN_BATCH_SIZE)
        eq_(data['page'], 2)
        eq_(data['batch_size'], settings.USERS_ADMIN_BATCH_SIZE)

        response = self.client.get(url, {'page': 11})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 101)
        # because it's sorted by last_login
        eq_(data['users'][0]['email'], user.email)
        eq_(len(data['users']), 1)
        eq_(data['page'], 11)
        eq_(data['batch_size'], settings.USERS_ADMIN_BATCH_SIZE)

    def test_users_data_pagination_bad_request(self):
        url = reverse('manage:users_data')
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.get(url, {'page': 0})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'page': -1})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'page': 'NaN'})
        eq_(response.status_code, 400)

    def test_users_data_filter(self):
        url = reverse('manage:users_data')
        self._login()

        group_a = Group.objects.create(name='Group A')
        group_b = Group.objects.create(name='Group B')

        def create_user(username, **kwargs):
            return User.objects.create(
                username=username,
                email=username + '@example.com',
                last_login=datetime.datetime.utcnow(),
                **kwargs
            )

        bob = create_user('bob')
        bob.groups.add(group_a)

        dick = create_user('dick')
        dick.groups.add(group_b)

        harry = create_user('harry')
        harry.groups.add(group_b)
        harry.groups.add(group_b)

        create_user('bill', is_active=False)

        # filter by email
        response = self.client.get(url, {'email': 'b'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 2)
        eq_(
            ['bill@example.com', 'bob@example.com'],
            [x['email'] for x in data['users']]
        )

        # filter by email and group
        response = self.client.get(url, {
            'email': 'b',
            'group': group_a.pk
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 1)
        eq_(
            ['bob@example.com'],
            [x['email'] for x in data['users']]
        )

        # filter by active and superuser
        response = self.client.get(url, {
            'active': '1',
            'superuser': '-1'
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 3)
        eq_(
            ['harry@example.com', 'dick@example.com', 'bob@example.com'],
            [x['email'] for x in data['users']]
        )

        # don't send in junk
        response = self.client.get(url, {
            'group': 'xxx',
        })
        eq_(response.status_code, 400)

    def test_edit_user(self):
        group_a = Group.objects.create(name='Group A')
        group_b = Group.objects.create(name='Group B')

        bob = User.objects.create(
            username='bob',
            email='bob@example.com',
            is_active=False,
            is_superuser=True
        )
        bob.groups.add(group_a)

        url = reverse('manage:user', args=(bob.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('bob@example.com' in response.content)

        response = self.client.post(url, {
            'groups': group_b.pk,
            'is_active': 'true',
            'is_superuser': ''
        })
        eq_(response.status_code, 302)

        # reload from database
        bob = User.objects.get(pk=bob.pk)
        ok_(bob.is_active)
        ok_(not bob.is_superuser)
        eq_(list(bob.groups.all()), [group_b])

        # check that the event got logged
        event, = Log.objects.all()
        eq_(event.user, user)
        eq_(event.action, 'user.edit')
        eq_(event.extra['id'], bob.pk)
        change = event.extra['change']
        eq_(change['is_superuser'], [True, False])
        eq_(change['is_active'], [False, True])
        eq_(change['groups'], [['Group A'], ['Group B']])

    def test_groups(self):
        url = reverse('manage:groups')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        wackos = Group.objects.create(name='Wackos')
        # Attach a known permission to it
        permission = self._create_permission()
        wackos.permissions.add(permission)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Wackos' in response.content)
        ok_('Mess Around' in response.content)

    def test_group(self):
        url = reverse('manage:groups')
        user = self._login()
        ct = ContentType.objects.create(
            model='',
            app_label='crashstats.crashstats',
        )
        p1 = Permission.objects.create(
            name='Mess Around',
            codename='mess_around',
            content_type=ct
        )
        p2 = Permission.objects.create(
            name='Launch Missiles',
            codename='launch_missiles',
            content_type=ct
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(p1.name in response.content)
        ok_(p2.name in response.content)

        data = {
            'name': 'New Group',
            'permissions': [p2.id]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        group = Group.objects.get(name=data['name'])
        eq_(list(group.permissions.all()), [p2])

        # check that it got logged
        event, = Log.objects.all()
        eq_(event.user, user)
        eq_(event.action, 'group.add')
        eq_(event.extra, {
            'id': group.id,
            'name': 'New Group',
            'permissions': ['Launch Missiles']
        })

        # edit it
        edit_url = reverse('manage:group', args=(group.pk,))
        response = self.client.get(edit_url)
        eq_(response.status_code, 200)
        data = {
            'name': 'New New Group',
            'permissions': [p1.id]
        }
        response = self.client.post(edit_url, data)
        eq_(response.status_code, 302)
        group = Group.objects.get(name=data['name'])
        eq_(list(group.permissions.all()), [p1])

        event, = Log.objects.all()[:1]
        eq_(event.user, user)
        eq_(event.action, 'group.edit')
        eq_(event.extra['change']['name'], ['New Group', 'New New Group'])
        eq_(event.extra['change']['permissions'], [
            ['Launch Missiles'],
            ['Mess Around']
        ])

        # delete it
        response = self.client.post(url, {'delete': group.pk})
        eq_(response.status_code, 302)
        ok_(not Group.objects.filter(name=data['name']))

        event, = Log.objects.all()[:1]
        eq_(event.user, user)
        eq_(event.action, 'group.delete')
        eq_(event.extra['name'], data['name'])

    def test_analyze_model_fetches(self):
        self._login()
        url = reverse('manage:analyze_model_fetches')
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_render_graphics_devices_page(self):
        url = reverse('manage:graphics_devices')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

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
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'vendor_hex': 'abc123',
            'adapter_hex': 'xyz123',
        })
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content['total'], 1)
        eq_(
            content['hits'][0],
            {
                'vendor_hex': 'abc123',
                'adapter_hex': 'xyz123',
                'vendor_name': 'Logictech',
                'adapter_name': 'Webcamera'
            }
        )

    def test_graphics_devices_edit(self):
        user = self._login()
        url = reverse('manage:graphics_devices')

        def mocked_post(**payload):
            data = payload['data']
            eq_(
                data[0],
                {
                    'vendor_hex': 'abc123',
                    'adapter_hex': 'xyz123',
                    'vendor_name': 'Logictech',
                    'adapter_name': 'Webcamera'
                }
            )
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
        eq_(response.status_code, 302)
        ok_(url in response['location'])

        event, = Log.objects.all()
        eq_(event.user, user)
        eq_(event.action, 'graphicsdevices.add')
        eq_(event.extra['payload'], [data])
        eq_(event.extra['success'], True)

    def test_graphics_devices_csv_upload_pcidatabase_com(self):
        user = self._login()
        url = reverse('manage:graphics_devices')

        def mocked_post(**payload):
            data = payload['data']
            eq_(
                data[0],
                {
                    'vendor_hex': '0x0033',
                    'adapter_hex': '0x002f',
                    'vendor_name': 'Paradyne Corp.',
                    'adapter_name': '.43 ieee 1394 controller'
                }
            )
            eq_(len(data), 7)
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
            eq_(response.status_code, 302)
            ok_(url in response['location'])

        event, = Log.objects.all()
        eq_(event.user, user)
        eq_(event.action, 'graphicsdevices.post')
        eq_(event.extra['success'], True)
        eq_(event.extra['database'], 'pcidatabase.com')
        eq_(event.extra['no_lines'], 7)

    def test_graphics_devices_csv_upload_pci_ids(self):
        user = self._login()
        url = reverse('manage:graphics_devices')

        def mocked_post(**payload):
            data = payload['data']
            eq_(
                data[0],
                {
                    'vendor_hex': '0x0010',
                    'adapter_hex': '0x8139',
                    'vendor_name': 'Allied Telesis, Inc',
                    'adapter_name': 'AT-2500TX V3 Ethernet'
                }
            )
            eq_(len(data), 6)
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
            eq_(response.status_code, 302)
            ok_(url in response['location'])

        event, = Log.objects.all()
        eq_(event.user, user)
        eq_(event.action, 'graphicsdevices.post')
        eq_(event.extra['success'], True)
        eq_(event.extra['database'], 'pci.ids')
        eq_(event.extra['no_lines'], 6)

    def test_symbols_uploads(self):
        url = reverse('manage:symbols_uploads')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_supersearch_fields_missing(self):
        self._login()
        url = reverse('manage:supersearch_fields_missing')

        def mocked_supersearchfields_get_fields(**params):
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

        SuperSearchFields.implementation().get.side_effect = (
            mocked_supersearchfields_get_fields
        )
        SuperSearchMissingFields.implementation().get.side_effect = (
            mocked_supersearchfields_get_missing_fields
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('field_a' in response.content)
        ok_('namespace1.field_b' in response.content)
        ok_('namespace2.subspace1.field_c' in response.content)

    def test_create_product(self):

        def mocked_post(**options):
            eq_(options['product'], 'WaterCat')
            eq_(options['version'], '1.0')
            return True

        models.ProductVersions.implementation().post.side_effect = (
            mocked_post
        )

        user = self._login()
        url = reverse('manage:products')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('value="1.0"' in response.content)

        # first attempt to create an existing combo
        response = self.client.post(url, {
            'product': 'WaterWolf',
            'initial_version': '1.0'
        })
        eq_(response.status_code, 200)
        ok_('WaterWolf already exists' in response.content)

        # now with a new unique product
        response = self.client.post(url, {
            'product': 'WaterCat',
            'initial_version': '1.0'
        })
        eq_(response.status_code, 302)

        event, = Log.objects.all()
        eq_(event.user, user)
        eq_(event.action, 'product.add')
        eq_(event.extra['product'], 'WaterCat')

    def test_create_release(self):

        def mocked_release_post(**params):
            eq_(params['product'], 'WaterCat')
            eq_(params['version'], '19.0')
            eq_(params['beta_number'], 1)
            eq_(params['throttle'], 0)
            return True

        models.Releases.implementation().post.side_effect = mocked_release_post

        user = self._login()
        url = reverse('manage:releases')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # there should be a dropdown with some known platforms
        ok_('value="Windows"' in response.content)
        ok_('value="Mac OS X"' in response.content)

        # first attempt to create with a product version that doesn't exist
        now = datetime.datetime.utcnow()
        data = {
            'product': 'WaterCat',
            'version': '99.9',
            'update_channel': 'beta',
            'build_id': now.strftime('%Y%m%d%H%M'),
            'platform': 'Windows',
            'beta_number': '0',
            'release_channel': 'Beta',
            'throttle': '1'
        }

        # set some bad values that won't pass validation
        data['throttle'] = 'xxx'
        data['beta_number'] = 'yyy'
        data['version'] = '19.0'
        data['build_id'] = 'XX'
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('Must start with YYYYMMDD' in response.content)
        eq_(response.content.count('not a number'), 2)

        data['build_id'] = '20140101XXXXX'
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('Date older than 30 days' in response.content)

        # finally, all with good parameters
        data['beta_number'] = '1'
        data['throttle'] = '0'
        data['build_id'] = now.strftime('%Y%m%d%H%M')
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        event, = Log.objects.all()
        eq_(event.user, user)
        eq_(event.action, 'release.add')
        eq_(event.extra['product'], 'WaterCat')

    @mock.patch('requests.post')
    def test_create_release_with_null_beta_number(self, rpost):
        mock_calls = []

        def mocked_release_post(**params):
            mock_calls.append(True)
            eq_(params['beta_number'], None)
            return True

        models.Releases.implementation().post.side_effect = mocked_release_post

        self._login()

        now = datetime.datetime.utcnow()
        data = {
            'product': 'WaterWolf',
            'version': '99.9',
            'update_channel': 'beta',
            'build_id': now.strftime('%Y%m%d%H%M'),
            'platform': 'Windows',
            'beta_number': ' ',
            'release_channel': 'Beta',
            'throttle': '1'
        }
        url = reverse('manage:releases')
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        # make sure it really called the POST to /releases/release/
        ok_(mock_calls)

    def test_view_events_page(self):
        url = reverse('manage:events')
        response = self.client.get(url)
        eq_(response.status_code, 302)
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
        eq_(response.status_code, 200)
        # for the action filter drop-downs
        eq_(response.content.count('value="actionA"'), 1)
        eq_(response.content.count('value="actionB"'), 1)

    def test_events_data(self):
        url = reverse('manage:events_data')
        response = self.client.get(url)
        eq_(response.status_code, 302)
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
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 2 + settings.EVENTS_ADMIN_BATCH_SIZE * 2)
        # the most recent should be "actionB"
        eq_(len(data['events']), settings.EVENTS_ADMIN_BATCH_SIZE)
        first = data['events'][0]
        eq_(first['action'], 'actionB')
        eq_(first['extra'], {'bar': False})

        # try to go to another page
        response = self.client.get(url, {'page': 'xxx'})
        eq_(response.status_code, 400)
        response = self.client.get(url, {'page': '0'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'page': '2'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        first = data['events'][0]
        # we should now be on one of the actionX events
        eq_(first['action'], 'actionX')

        # we can filter by user
        response = self.client.get(url, {'user': 'other'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 1)

        # we can filter by action
        response = self.client.get(url, {'action': 'actionX'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], settings.EVENTS_ADMIN_BATCH_SIZE * 2)

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
        eq_(data['count'], 3)
        three, two, one = data['events']
        eq_(one['url'], reverse('manage:user', args=(user.id,)))
        eq_(two['url'], reverse('manage:group', args=(group.id,)))
        eq_(three['url'], reverse('manage:group', args=(group.id,)))

    def test_api_tokens(self):
        permission = self._create_permission()
        url = reverse('manage:api_tokens')
        response = self.client.get(url)
        # because we're not logged in
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # expects some permissions to be available as dropdowns
        ok_(
            '<option value="%s">%s</option>' % (
                permission.id,
                permission.name
            ) in response.content
        )

    def test_create_api_token(self):
        superuser = self._login()
        user = User.objects.create_user(
            'user',
            'user@example.com',
            'secret'
        )
        permission = self._create_permission()
        # the user must belong to a group that has this permission
        wackos = Group.objects.create(name='Wackos')
        wackos.permissions.add(permission)
        user.groups.add(wackos)
        assert user.has_perm('crashstats.' + permission.codename)

        url = reverse('manage:api_tokens')
        response = self.client.post(url, {
            'user': user.email.upper(),
            'permissions': [permission.id],
            'notes': 'Some notes',
            'expires': 7
        })
        eq_(response.status_code, 302)
        token = Token.objects.get(
            user=user,
            notes='Some notes',
        )
        eq_(list(token.permissions.all()), [permission])
        lasting = (timezone.now() - token.expires).days * -1
        eq_(lasting, 7)

        event, = Log.objects.all()

        eq_(event.user, superuser)
        eq_(event.action, 'api_token.create')
        eq_(event.extra['notes'], 'Some notes')
        ok_(event.extra['expires'])
        eq_(event.extra['expires_days'], 7)
        eq_(event.extra['permissions'], permission.name)

    def test_create_api_token_with_no_permissions(self):
        superuser = self._login()
        user = User.objects.create_user(
            'user',
            'user@example.com',
            'secret'
        )
        permission = self._create_permission()
        # the user must belong to a group that has this permission
        wackos = Group.objects.create(name='Wackos')
        wackos.permissions.add(permission)
        user.groups.add(wackos)
        assert user.has_perm('crashstats.' + permission.codename)

        url = reverse('manage:api_tokens')
        response = self.client.post(url, {
            'user': user.email.upper(),
            'notes': 'Some notes',
            'expires': 7
        })
        eq_(response.status_code, 302)
        token = Token.objects.get(
            user=user,
            notes='Some notes',
        )
        eq_(list(token.permissions.all()), [])
        lasting = (timezone.now() - token.expires).days * -1
        eq_(lasting, 7)

        event, = Log.objects.all()

        eq_(event.user, superuser)
        eq_(event.action, 'api_token.create')
        eq_(event.extra['notes'], 'Some notes')
        ok_(event.extra['expires'])
        eq_(event.extra['expires_days'], 7)
        eq_(event.extra['permissions'], '')

    def test_create_api_token_rejected(self):
        self._login()
        user = User.objects.create_user(
            'koala',
            'koala@example.com',
            'secret'
        )
        permission = self._create_permission()
        url = reverse('manage:api_tokens')
        response = self.client.post(url, {
            'user': 'xxx',
            'permissions': [permission.id],
            'notes': '',
            'expires': 7
        })
        eq_(response.status_code, 200)
        ok_('No user found by that email address' in response.content)
        response = self.client.post(url, {
            'user': 'k',  # there will be two users whose email starts with k
            'permissions': [permission.id],
            'notes': '',
            'expires': 7
        })
        eq_(response.status_code, 200)
        ok_(
            'More than one user found by that email address'
            in response.content
        )
        response = self.client.post(url, {
            'user': 'koala@example',
            'permissions': [permission.id],
            'notes': '',
            'expires': 7
        })
        eq_(response.status_code, 200)
        ok_(
            'koala@example.com does not have the permission '
            '&quot;Mess Around&quot;'
            in response.content
        )
        ok_(
            'koala@example.com has no permissions!'
            in response.content
        )
        # suppose the user has some other permission, only
        permission2 = self._create_permission(
            'Do Things',
            'do_things'
        )
        group = Group.objects.create(name='Noobs')
        group.permissions.add(permission2)
        user.groups.add(group)
        assert user.has_perm('crashstats.do_things')
        response = self.client.post(url, {
            'user': 'koala@example',
            'permissions': [permission.id],
            'notes': '',
            'expires': 7
        })
        eq_(response.status_code, 200)
        ok_(
            'koala@example.com does not have the permission '
            '&quot;Mess Around&quot;'
            in response.content
        )
        ok_(
            'Only permissions possible are: Do Things'
            in response.content
        )

        # you can't create a token for an inactive user
        user.is_active = False
        user.save()
        response = self.client.post(url, {
            'user': 'koala',
            'permissions': [permission.id],
            'notes': '',
            'expires': 7
        })
        eq_(response.status_code, 200)
        ok_(
            'koala@example.com is not an active user'
            in response.content
        )

    def test_api_tokens_data(self):
        url = reverse('manage:api_tokens_data')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(result['tokens'], [])
        eq_(result['count'], 0)
        eq_(result['page'], 1)
        eq_(result['batch_size'], settings.API_TOKENS_ADMIN_BATCH_SIZE)

        expires = timezone.now()
        expires += datetime.timedelta(
            days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS
        )
        token = Token.objects.create(
            user=user,
            notes='Some notes',
            expires=expires
        )
        assert token.key  # automatically generated
        permission = self._create_permission()
        token.permissions.add(permission)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        expected_token = {
            'created': token.created.isoformat(),
            'notes': 'Some notes',
            'expires': expires.isoformat(),
            'id': token.id,
            'expired': False,
            'permissions': [permission.name],
            'user': user.email,
            'key': token.key,
        }
        eq_(result['tokens'], [expected_token])
        eq_(result['count'], 1)

        # mess with the page parameter
        response = self.client.get(url, {'page': '0'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'expired': 'junk'})
        eq_(response.status_code, 400)

        # filter by email
        response = self.client.get(url, {'email': user.email[:5]})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(result['tokens'], [expected_token])
        eq_(result['count'], 1)
        response = self.client.get(url, {'user': 'junk'})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(result['tokens'], [])
        eq_(result['count'], 0)

        # filter by key
        response = self.client.get(url, {'key': token.key[:5]})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(result['tokens'], [expected_token])
        eq_(result['count'], 1)
        response = self.client.get(url, {'key': 'junk'})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(result['tokens'], [])
        eq_(result['count'], 0)

        # filter by expired
        response = self.client.get(url, {'expired': 'no'})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(result['tokens'], [expected_token])
        eq_(result['count'], 1)
        response = self.client.get(url, {'expired': 'yes'})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(result['tokens'], [])
        eq_(result['count'], 0)
        token.expires = timezone.now() - datetime.timedelta(days=1)
        token.save()
        response = self.client.get(url, {'expired': 'yes'})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        expected_token['expires'] = token.expires.isoformat()
        expected_token['expired'] = True
        eq_(result['tokens'], [expected_token])
        eq_(result['count'], 1)

    def test_api_tokens_delete(self):
        url = reverse('manage:api_tokens_delete')
        response = self.client.get(url)
        eq_(response.status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 302)
        user = self._login()
        response = self.client.post(url)
        eq_(response.status_code, 400)
        response = self.client.post(url, {'id': '99999'})
        eq_(response.status_code, 404)

        expires = timezone.now()
        expires += datetime.timedelta(
            days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS
        )
        token = Token.objects.create(
            user=user,
            notes='Some notes',
            expires=expires
        )
        assert token.key  # automatically generated
        permission = self._create_permission()
        token.permissions.add(permission)

        response = self.client.post(url, {'id': token.id})
        eq_(response.status_code, 200)  # it's AJAX

        ok_(not Token.objects.all())

        event, = Log.objects.all()

        eq_(event.user, user)
        eq_(event.action, 'api_token.delete')
        eq_(event.extra['notes'], 'Some notes')
        eq_(event.extra['user'], user.email)
        eq_(event.extra['permissions'], permission.name)

    def test_status_message(self):
        url = reverse('manage:status_message')

        # Test while logged out.
        response = self.client.get(url)
        eq_(response.status_code, 302)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # expects some severity options to be available as dropdowns
        ok_(
            '<option value="%s">%s</option>' % (
                'critical',
                'Critical'
            ) in response.content
        )

    def test_create_status_message(self):
        url = reverse('manage:status_message')

        # Test while logged out.
        response = self.client.post(url)
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.post(url)
        eq_(response.status_code, 200)
        ok_('This field is required' in response.content)

        response = self.client.post(url, {
            'message': 'Foo',
            'severity': 'critical'
        })
        eq_(response.status_code, 302)

        event, = Log.objects.all()

        eq_(event.user, user)
        eq_(event.action, 'status_message.create')
        eq_(event.extra['severity'], 'critical')

    def test_disable_status_message(self):
        url = reverse('manage:status_message_disable', args=('99999',))
        response = self.client.get(url)
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 404)

        status = StatusMessage.objects.create(
            message='foo',
            severity='critical',
        )
        url = reverse('manage:status_message_disable', args=(status.id,))

        response = self.client.post(url)
        eq_(response.status_code, 302)  # redirect on success

        # Verify there is no enabled statuses anymore.
        ok_(not StatusMessage.objects.filter(enabled=True))

        event, = Log.objects.all()

        eq_(event.user, user)
        eq_(event.action, 'status_message.disable')

    def test_crash_me_now(self):
        url = reverse('manage:crash_me_now')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        assert_raises(
            NameError,
            self.client.post,
            url,
            {
                'exception_type': 'NameError',
                'exception_value': 'Crash!'
            }
        )

    def test_symbols_uploads_data_pagination(self):
        url = reverse('manage:symbols_uploads_data')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self._login()

        other = User.objects.create(username='o', email='other@mozilla.com')
        for i in range(settings.SYMBOLS_UPLOADS_ADMIN_BATCH_SIZE):
            SymbolsUpload.objects.create(
                user=other,
                filename='file-%d.zip' % i,
                size=1000 + i,
                content='Some Content'
            )
        # add this last so it shows up first
        user = User.objects.create(username='user', email='user@mozilla.com')
        upload = SymbolsUpload.objects.create(
            user=user,
            filename='file.zip',
            size=123456,
            content='Some Content'
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], settings.SYMBOLS_UPLOADS_ADMIN_BATCH_SIZE + 1)
        eq_(data['batch_size'], settings.SYMBOLS_UPLOADS_ADMIN_BATCH_SIZE)
        eq_(data['page'], 1)
        items = data['items']
        eq_(len(items), settings.SYMBOLS_UPLOADS_ADMIN_BATCH_SIZE)
        first, = items[:1]
        eq_(first['id'], upload.id)
        eq_(first['created'], upload.created.isoformat())
        eq_(first['filename'], 'file.zip')
        eq_(first['size'], 123456)
        eq_(first['url'], reverse('symbols:content', args=(first['id'],)))
        eq_(first['user'], {
            'email': user.email,
            'url': reverse('manage:user', args=(user.id,)),
            'id': user.id,
        })

        # let's go to page 2
        response = self.client.get(url, {'page': 2})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], settings.SYMBOLS_UPLOADS_ADMIN_BATCH_SIZE + 1)
        items = data['items']
        eq_(len(items), 1)
        eq_(data['page'], 2)

        # filter by user email
        response = self.client.get(url, {'email': user.email[:5].upper()})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 1)
        first, = data['items']
        eq_(first['user']['id'], user.id)

        # filter by filename
        response = self.client.get(url, {'filename': 'FILE.ZI'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 1)
        first, = data['items']
        eq_(first['filename'], 'file.zip')

    def test_symbols_uploads_data_content_search(self):
        url = reverse('manage:symbols_uploads_data')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self._login()

        other = User.objects.create(username='o', email='other@mozilla.com')
        for i in range(3):
            SymbolsUpload.objects.create(
                user=other,
                filename='file-%d.zip' % i,
                size=1000 + i,
                content='Some Content {}'.format(i)
            )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 3)

        response = self.client.get(url, {'content': 'Some Content'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 3)

        response = self.client.get(url, {'content': 'Some Content 1'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 1)

        response = self.client.get(url, {'content': 'Some Content X'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 0)

    def test_symbols_uploads_data_pagination_bad_request(self):
        url = reverse('manage:symbols_uploads_data')
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.get(url, {'page': 0})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'page': -1})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'page': 'NaN'})
        eq_(response.status_code, 400)

    def test_reprocessing(self):
        url = reverse('manage:reprocessing')
        response = self.client.get(url)
        eq_(response.status_code, 302)

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
        eq_(response.status_code, 200)

        response = self.client.post(
            url,
            {'crash_id': 'junk'},
        )
        eq_(response.status_code, 200)
        ok_('Does not appear to be a valid crash ID' in response.content)

        response = self.client.post(
            url,
            {'crash_id': good_crash_id},
        )
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            url + '?crash_id=' + good_crash_id
        )

        response = self.client.post(
            url,
            {'crash_id': bad_crash_id},
        )
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            url  # note lack of `?crash_id=...`
        )
