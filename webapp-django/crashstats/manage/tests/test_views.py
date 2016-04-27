import json
import datetime
import os
import re
import urlparse

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Group, Permission
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

import mock
from nose.tools import eq_, ok_, assert_raises
from eventlog.models import Log

from crashstats.symbols.models import SymbolsUpload
from crashstats.tokens.models import Token
from crashstats.supersearch.models import (
    SuperSearchFields,
    SuperSearchMissingFields,
)
from crashstats.crashstats import models
from crashstats.crashstats.tests.test_views import (
    BaseTestViews,
    Response
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
        self.user = User.objects.create_user('kairo', 'kai@ro.com', 'secret')
        self.user.is_superuser = is_superuser
        # django doesn't set this unless the user has actually signed in
        self.user.last_login = datetime.datetime.utcnow()
        self.user.save()
        assert self.client.login(username='kairo', password='secret')

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
        ok_('You need to be a superuser to access this' in response.content)

    def test_home_page_signed_in(self):
        self._login()
        # at the moment it just redirects
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        eq_(response.status_code, 200)

        # certain links on that page
        featured_versions_url = reverse('manage:featured_versions')
        ok_(featured_versions_url in response.content)
        fields_url = reverse('manage:fields')
        ok_(fields_url in response.content)
        users_url = reverse('manage:users')
        ok_(users_url in response.content)
        products_url = reverse('manage:products')
        ok_(products_url in response.content)
        releases_url = reverse('manage:releases')
        ok_(releases_url in response.content)

    @mock.patch('requests.put')
    @mock.patch('requests.get')
    def test_featured_versions(self, rget, rput):
        self._login()
        url = reverse('manage:featured_versions')

        put_calls = []  # some mutable

        def mocked_put(url, **options):
            assert '/releases/featured' in url
            data = options['data']
            put_calls.append(data)
            return Response("true")

        rput.side_effect = mocked_put

        def mocked_product_versions(**params):
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)

            hits = [
                {
                    'product': 'WaterWolf',
                    'is_featured': True,
                    'throttle': 90.0,
                    'end_date': tomorrow,
                    'product': 'WaterWolf',
                    'release': 'Nightly',
                    'version': '19.0.1',
                    'has_builds': True,
                    'start_date': today,
                },
                {
                    'product': 'WaterWolf',
                    'is_featured': False,
                    'throttle': 33.333,
                    'end_date': today,
                    'product': 'WaterWolf',
                    'release': 'Nightly',
                    'version': '18.0.1',
                    'has_builds': True,
                    'start_date': today,
                },
            ]
            return {
                'hits': hits,
                'total': len(hits),
            }

        models.ProductVersions.implementation().get.side_effect = (
            mocked_product_versions
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('19.0.1' in response.content)
        ok_('18.0.1' in response.content)

        # also, note how the percentages are written out
        # (know thy fixtures)
        ok_('90%' in response.content)
        ok_('33.3%' in response.content)

        input_regex = re.compile('<input .*?>', re.M | re.DOTALL)
        checkboxes = [
            x for x in
            input_regex.findall(response.content)
            if 'type="checkbox"' in x
        ]
        eq_(len(checkboxes), 2)
        checkboxes_by_value = dict(
            (re.findall('value="(.*)"', x)[0], x)
            for x in checkboxes
        )
        ok_('checked' in checkboxes_by_value['19.0.1'])
        ok_('checked' not in checkboxes_by_value['18.0.1'])

        # post in a change
        update_url = reverse('manage:update_featured_versions')
        response = self.client.post(update_url, {
            'WaterWolf': '18.0.1'
        })
        eq_(response.status_code, 302)
        put_call = put_calls[0]
        eq_(put_call['WaterWolf'], '18.0.1')

        # check that it got logged
        event, = Log.objects.all()
        eq_(event.user, self.user)
        eq_(event.action, 'featured_versions.update')
        eq_(event.extra['success'], True)
        eq_(event.extra['data'], {'WaterWolf': ['18.0.1']})

    def test_fields(self):
        url = reverse('manage:fields')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_field_lookup(self, rget):
        url = reverse('manage:field_lookup')

        response = self.client.get(url)
        eq_(response.status_code, 302)

        self._login()
        response = self.client.get(url)
        # missing 'name' parameter
        eq_(response.status_code, 400)

        def mocked_get(url, params, **options):
            assert '/field' in url

            ok_('name' in params)
            eq_('Android_Display', params['name'])

            return Response("""
            {
                "name": "Android_Display",
                "product": null,
                "transforms": {
                    "1.X processed json": "",
                    "collector:raw json": "",
                    "data name": "Android_Display",
                    "database": "",
                    "mdsw pipe dump": "",
                    "pj transform": "",
                    "processed json 2012": "",
                    "processor transform": "",
                    "ted's mdsw json": ""
                }
            }
            """)

        rget.side_effect = mocked_get

        response = self.client.get(url, {'name': 'Android_Display'})
        eq_(response.status_code, 200)

        data = json.loads(response.content)
        eq_(data['product'], None)
        eq_(len(data['transforms']), 9)

    def test_skiplist_link(self):
        self._login()
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        assert response.status_code == 200
        ok_(reverse('manage:skiplist') in response.content)

    def test_skiplist_admin_page(self):
        url = reverse('manage:skiplist')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_skiplist_data(self, rget):
        self._login()

        def mocked_get(url, params, **options):
            assert '/skiplist' in url

            if (
                'category' in params and 'suffix' == params['category'] and
                'rule' in params and 'Bar' == params['rule']
            ):
                return Response("""
                {
                    "hits": [
                        {"category": "suffix", "rule": "Bar"}
                    ],
                    "total": 1
                }
                """)
            elif 'category' in params and 'suffix' == params['category']:
                return Response("""
                {
                    "hits": [
                        {"category": "suffix", "rule": "Bar"},
                        {"category": "suffix", "rule": "Foo"}
                    ],
                    "total": 2
                }
                """)
            elif 'rule' in params and 'Bar' == params['rule']:
                return Response("""
                {
                    "hits": [
                        {"category": "prefix", "rule": "Bar"},
                        {"category": "suffix", "rule": "Bar"}
                    ],
                    "total": 2
                }
                """)
            else:
                return Response("""
                {
                    "hits": [
                        {"category": "prefix", "rule": "Bar"},
                        {"category": "prefix", "rule": "Foo"},
                        {"category": "suffix", "rule": "Bar"},
                        {"category": "suffix", "rule": "Foo"}
                    ],
                    "total": 4
                }
                """)

        rget.side_effect = mocked_get

        url = reverse('manage:skiplist_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        expect = {
            'hits': [
                {'category': 'prefix', 'rule': 'Bar'},
                {'category': 'prefix', 'rule': 'Foo'},
                {'category': 'suffix', 'rule': 'Bar'},
                {'category': 'suffix', 'rule': 'Foo'}
            ],
            'total': 4
        }
        eq_(data, expect)

        # filter by category
        response = self.client.get(url, {'category': 'suffix'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        expect = {
            'hits': [
                {'category': 'suffix', 'rule': 'Bar'},
                {'category': 'suffix', 'rule': 'Foo'}
            ],
            'total': 2
        }
        eq_(data, expect)

        # filter by rule
        response = self.client.get(url, {'rule': 'Bar'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        expect = {
            'hits': [
                {'category': 'prefix', 'rule': 'Bar'},
                {'category': 'suffix', 'rule': 'Bar'},
            ],
            'total': 2
        }
        eq_(data, expect)

        # filter by rule and category
        response = self.client.get(
            url,
            {'rule': 'Bar', 'category': 'suffix'}
        )
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        expect = {
            'hits': [
                {'category': 'suffix', 'rule': 'Bar'},
            ],
            'total': 1
        }
        eq_(data, expect)

    @mock.patch('requests.post')
    def test_skiplist_add(self, rpost):

        def mocked_post(url, **options):
            assert '/skiplist' in url, url
            ok_(options['data'].get('category'))
            ok_(options['data'].get('rule'))
            return Response("true")

        rpost.side_effect = mocked_post

        self._login()
        url = reverse('manage:skiplist_add')
        # neither
        response = self.client.post(url)
        eq_(response.status_code, 400)
        # only category
        response = self.client.post(url, {'category': 'suffix'})
        eq_(response.status_code, 400)
        # only rule
        response = self.client.post(url, {'rule': 'Foo'})
        eq_(response.status_code, 400)

        response = self.client.post(
            url,
            {'rule': 'Foo', 'category': 'suffix'}
        )
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        # check that it got logged
        event, = Log.objects.all()
        eq_(event.user, self.user)
        eq_(event.action, 'skiplist.add')
        eq_(event.extra['success'], True)
        eq_(event.extra['data'], {
            'category': 'suffix',
            'rule': 'Foo'
        })

    @mock.patch('requests.delete')
    def test_skiplist_delete(self, rdelete):

        def mocked_delete(url, params, **options):
            assert '/skiplist' in url, url
            ok_('category' in params)
            eq_('suffix', params['category'])

            ok_('rule' in params)
            eq_('Foo', params['rule'])

            return Response("true")

        rdelete.side_effect = mocked_delete

        self._login()
        url = reverse('manage:skiplist_delete')
        # neither
        response = self.client.post(url)
        eq_(response.status_code, 400)
        # only category
        response = self.client.post(url, {'category': 'suffix'})
        eq_(response.status_code, 400)
        # only rule
        response = self.client.post(url, {'rule': 'Foo'})
        eq_(response.status_code, 400)

        response = self.client.post(
            url,
            {'rule': 'Foo', 'category': 'suffix'}
        )
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        # check that it got logged
        event, = Log.objects.all()
        eq_(event.user, self.user)
        eq_(event.action, 'skiplist.delete')
        eq_(event.extra['success'], True)
        eq_(event.extra['data'], {
            'category': 'suffix',
            'rule': 'Foo'
        })

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
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 1)
        eq_(data['users'][0]['email'], self.user.email)
        eq_(data['users'][0]['id'], self.user.pk)
        eq_(data['users'][0]['is_superuser'], True)
        eq_(data['users'][0]['is_active'], True)
        eq_(data['users'][0]['groups'], [])

        austrians = Group.objects.create(name='Austrians')
        self.user.groups.add(austrians)

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
        self._login()
        self.user.last_login -= datetime.timedelta(days=365)
        self.user.save()
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
        eq_(data['users'][0]['email'], self.user.email)
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
        self._login()
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
        eq_(event.user, self.user)
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
        self._login()
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
        eq_(event.user, self.user)
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
        eq_(event.user, self.user)
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
        eq_(event.user, self.user)
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
        self._login()
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
        eq_(event.user, self.user)
        eq_(event.action, 'graphicsdevices.add')
        eq_(event.extra['payload'], [data])
        eq_(event.extra['success'], True)

    def test_graphics_devices_csv_upload_pcidatabase_com(self):
        self._login()
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
        eq_(event.user, self.user)
        eq_(event.action, 'graphicsdevices.post')
        eq_(event.extra['success'], True)
        eq_(event.extra['database'], 'pcidatabase.com')
        eq_(event.extra['no_lines'], 7)

    def test_graphics_devices_csv_upload_pci_ids(self):
        self._login()
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
        eq_(event.user, self.user)
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

    def test_supersearch_fields(self):
        self._login()
        url = reverse('manage:supersearch_fields')

        def mocked_supersearchfields_get_fields(**params):
            return {
                'signature': {
                    'name': 'signature',
                    'namespace': 'processed_crash',
                    'in_database_name': 'signature',
                    'query_type': 'string',
                    'form_field_choices': None,
                    'permissions_needed': [],
                    'default_value': None,
                    'is_exposed': True,
                    'is_returned': True,
                    'is_mandatory': False,
                },
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

        SuperSearchFields.implementation().get.side_effect = (
            mocked_supersearchfields_get_fields
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('signature' in response.content)
        ok_('string' in response.content)
        ok_('product' in response.content)
        ok_('enum' in response.content)

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

    def test_supersearch_field(self):
        self._login()
        url = reverse('manage:supersearch_field')

        def mocked_supersearchfields_get_fields(**params):
            return {
                'signature': {
                    'name': 'signature',
                    'namespace': 'processed_crash',
                    'in_database_name': 'signature',
                    'query_type': 'string',
                    'form_field_choices': None,
                    'permissions_needed': [],
                    'default_value': None,
                    'is_exposed': True,
                    'is_returned': True,
                    'is_mandatory': False,
                },
                'platform': {
                    'name': 'platform',
                    'namespace': 'processed_crash',
                    'in_database_name': 'platform',
                    'query_type': 'enum',
                    'form_field_choices': None,
                    'permissions_needed': [],
                    'default_value': None,
                    'is_exposed': True,
                    'is_returned': True,
                    'is_mandatory': False,
                }
            }

        SuperSearchFields.implementation().get.side_effect = (
            mocked_supersearchfields_get_fields
        )

        # Test when creating a new field.
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('signature' not in response.content)
        ok_('platform' not in response.content)

        # Test when creating a new field with some default values.
        response = self.client.get(
            url + '?full_name=namespace.subspace.field_z'
        )
        eq_(response.status_code, 200)
        ok_('field_z' in response.content)
        ok_('namespace.subspace' in response.content)
        ok_('namespace.subspace.field_z' not in response.content)

        # Test when editing an existing field.
        response = self.client.get(url, {'name': 'signature'})
        eq_(response.status_code, 200)
        ok_('signature' in response.content)
        ok_('string' in response.content)
        ok_('platform' not in response.content)

        # Test a missing field.
        response = self.client.get(url, {'name': 'unknown'})
        eq_(response.status_code, 400)

    def test_supersearch_field_create(self):
        self._login()
        url = reverse('manage:supersearch_field_create')

        def mocked_supersearchfields_get_fields(**params):
            return {}

        def mocked_supersearchfields_create_field(**params):
            assert 'name' in params
            assert 'in_database_name' in params
            return True

        SuperSearchFields.implementation().get.side_effect = (
            mocked_supersearchfields_get_fields
        )
        SuperSearchFields.implementation().create_field.side_effect = (
            mocked_supersearchfields_create_field
        )

        response = self.client.post(
            url,
            {
                'name': 'something',
                'in_database_name': 'something',
            }
        )
        eq_(response.status_code, 302)

        event, = Log.objects.all()
        eq_(event.user, self.user)
        eq_(event.action, 'supersearch_field.post')
        eq_(event.extra['name'], 'something')

        response = self.client.post(url)
        eq_(response.status_code, 400)

        response = self.client.post(url, {'name': 'abcd'})
        eq_(response.status_code, 400)

        response = self.client.post(url, {'in_database_name': 'bar'})
        eq_(response.status_code, 400)

    def test_supersearch_field_update(self):
        self._login()
        url = reverse('manage:supersearch_field_update')

        # Create a permission to test permission validation.

        ct = ContentType.objects.create(
            model='',
            app_label='crashstats.crashstats',
        )
        Permission.objects.create(
            name='I can haz permission!',
            codename='i.can.haz.permission',
            content_type=ct
        )

        def mocked_supersearchfields_get_fields(**params):
            return {}

        def mocked_supersearchfields_update_field(**data):
            ok_('name' in data)
            ok_('description' in data)
            ok_('is_returned' in data)
            ok_('form_field_choices' in data)
            ok_('permissions_needed' in data)

            ok_(not data['is_returned'])
            ok_('' not in data['form_field_choices'])

            eq_(
                data['permissions_needed'],
                ['crashstats.i.can.haz.permission']
            )
            return True

        SuperSearchFields.implementation().get.side_effect = (
            mocked_supersearchfields_get_fields
        )
        SuperSearchFields.implementation().update_field.side_effect = (
            mocked_supersearchfields_update_field
        )

        response = self.client.post(
            url,
            {
                'name': 'something',
                'in_database_name': 'something',
                'description': 'hello world',
                'is_returned': False,
                'form_field_choices': ['', 'a choice', 'another choice'],
                'permissions_needed': ['', 'crashstats.i.can.haz.permission'],
            }
        )
        eq_(response.status_code, 302)

        event, = Log.objects.all()
        eq_(event.user, self.user)
        eq_(event.action, 'supersearch_field.put')
        eq_(event.extra['name'], 'something')

        response = self.client.post(url)
        eq_(response.status_code, 400)

        response = self.client.post(url, {'name': 'foo'})
        eq_(response.status_code, 400)

        response = self.client.post(url, {'in_database_name': 'bar'})
        eq_(response.status_code, 400)

    def test_supersearch_field_delete(self):
        self._login()
        url = reverse('manage:supersearch_field_delete')

        def mocked_supersearchfields_get_fields(**params):
            return {}

        def mocked_supersearchfields_delete_field(**params):
            assert 'name' in params
            return True

        SuperSearchFields.implementation().get.side_effect = (
            mocked_supersearchfields_get_fields
        )
        SuperSearchFields.implementation().delete_field.side_effect = (
            mocked_supersearchfields_delete_field
        )

        response = self.client.get(url, {'name': 'signature'})
        eq_(response.status_code, 302)

        event, = Log.objects.all()
        eq_(event.user, self.user)
        eq_(event.action, 'supersearch_field.delete')
        eq_(event.extra['name'], 'signature')

        response = self.client.get(url)
        eq_(response.status_code, 400)

    def test_create_product(self):

        def mocked_post(**options):
            eq_(options['product'], 'WaterCat')
            eq_(options['version'], '1.0')
            return True

        models.ProductVersions.implementation().post.side_effect = (
            mocked_post
        )

        self._login()
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
        eq_(event.user, self.user)
        eq_(event.action, 'product.add')
        eq_(event.extra['product'], 'WaterCat')

    @mock.patch('requests.post')
    def test_create_release(self, rpost):

        def mocked_post(url, **options):
            assert '/releases/release/' in url, url
            data = options['data']
            eq_(data['product'], 'WaterCat')
            eq_(data['version'], '19.0')
            eq_(data['beta_number'], 1)
            eq_(data['throttle'], 0)
            return Response(True)

        rpost.side_effect = mocked_post

        self._login()
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
        eq_(event.user, self.user)
        eq_(event.action, 'release.add')
        eq_(event.extra['product'], 'WaterCat')

    @mock.patch('requests.post')
    def test_create_release_with_null_beta_number(self, rpost):
        mock_calls = []

        def mocked_post(url, **options):
            assert '/releases/release/' in url, url
            mock_calls.append(url)
            data = options['data']
            eq_(data['beta_number'], None)
            return Response(True)

        rpost.side_effect = mocked_post

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
        self._login()

        # this page will iterate over all unique possible Log actions
        Log.objects.create(
            user=self.user,
            action='actionA'
        )
        Log.objects.create(
            user=self.user,
            action='actionB'
        )
        Log.objects.create(
            user=self.user,
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
        self._login()

        Log.objects.create(
            user=self.user,
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
        self._login()

        Log.objects.create(
            user=self.user,
            action='user.edit',
            extra={'id': self.user.id}
        )

        group = Group.objects.create(name='Wackos')
        Log.objects.create(
            user=self.user,
            action='group.add',
            extra={'id': group.id}
        )
        Log.objects.create(
            user=self.user,
            action='group.edit',
            extra={'id': group.id}
        )
        Log.objects.create(
            user=self.user,
            action='supersearch_field.post',
            extra={'name': 'sig1'}
        )
        Log.objects.create(
            user=self.user,
            action='supersearch_field.put',
            extra={'name': 'sig2'}
        )
        url = reverse('manage:events_data')
        response = self.client.get(url)
        data = json.loads(response.content)
        eq_(data['count'], 5)
        five, four, three, two, one = data['events']
        eq_(one['url'], reverse('manage:user', args=(self.user.id,)))
        eq_(two['url'], reverse('manage:group', args=(group.id,)))
        eq_(three['url'], reverse('manage:group', args=(group.id,)))
        eq_(four['url'], reverse('manage:supersearch_field') + '?name=sig1')
        eq_(five['url'], reverse('manage:supersearch_field') + '?name=sig2')

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
        self._login()
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

        eq_(event.user, self.user)
        eq_(event.action, 'api_token.create')
        eq_(event.extra['notes'], 'Some notes')
        ok_(event.extra['expires'])
        eq_(event.extra['expires_days'], 7)
        eq_(event.extra['permissions'], permission.name)

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
        self._login()
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
            user=self.user,
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
            'user': self.user.email,
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
        response = self.client.get(url, {'email': self.user.email[:5]})
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
        self._login()
        response = self.client.post(url)
        eq_(response.status_code, 400)
        response = self.client.post(url, {'id': '99999'})
        eq_(response.status_code, 404)

        expires = timezone.now()
        expires += datetime.timedelta(
            days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS
        )
        token = Token.objects.create(
            user=self.user,
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

        eq_(event.user, self.user)
        eq_(event.action, 'api_token.delete')
        eq_(event.extra['notes'], 'Some notes')
        eq_(event.extra['user'], self.user.email)
        eq_(event.extra['permissions'], permission.name)

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

        def mocked_reprocess(crash_id):
            if crash_id == good_crash_id:
                return True
            elif crash_id == bad_crash_id:
                return
            raise NotImplementedError(crash_id)

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
