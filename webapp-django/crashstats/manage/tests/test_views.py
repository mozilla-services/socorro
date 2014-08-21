import json
import datetime
import os
import re
import urlparse

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Group, Permission
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import utc

import mock
from nose.tools import eq_, ok_

from crashstats.symbols.models import SymbolsUpload
from crashstats.crashstats.tests.test_views import (
    BaseTestViews,
    Response
)


class TestViews(BaseTestViews):

    @mock.patch('requests.get')
    def setUp(self, rget):
        super(TestViews, self).setUp()

        # we do this here so that the current/versions thing
        # is cached since that's going to be called later
        # in every view more or less
        def mocked_get(url, **options):
            if '/products' in url:
                return Response("""
                {
                  "hits": [
                    {
                        "is_featured": true,
                        "throttle": 1.0,
                        "end_date": "string",
                        "start_date": "integer",
                        "build_type": "string",
                        "product": "WaterWolf",
                        "version": "19.0",
                        "has_builds": true
                    }],
                    "total": "1"
                }
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        from crashstats.crashstats.models import (
            CurrentProducts, CurrentVersions
        )
        versions = '+'.join([
            '%s:%s' % (ver['product'], ver['version'])
            for ver in CurrentVersions().get()
            if ver['product'] == settings.DEFAULT_PRODUCT
        ])
        api = CurrentProducts()
        # because WaterWolf is the default product and because
        # BaseTestViews.setUp calls CurrentVersions already, we need to
        # prepare this call so that each call to the home page can use the
        # cache
        api.get(versions=versions)

    def _login(self, is_superuser=True):
        self.user = User.objects.create_user('kairo', 'kai@ro.com', 'secret')
        self.user.is_superuser = is_superuser
        self.user.save()
        assert self.client.login(username='kairo', password='secret')

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

        def mocked_get(url, **options):
            if 'products' in url:
                today = datetime.date.today()
                tomorrow = today + datetime.timedelta(days=1)
                yesterday = today - datetime.timedelta(days=1)
                dates = {
                    'start_date_19': today,
                    'end_date_19': tomorrow,
                    'start_date_18': today,
                    'end_date_18': today,
                    'start_date_17': tomorrow,
                    'end_date_17': tomorrow + datetime.timedelta(days=1),
                    'start_date_16': yesterday - datetime.timedelta(days=1),
                    'end_date_16': yesterday,
                }
                return Response("""
                    {
                        "products": [
                            "WaterWolf"
                        ],
                        "hits": {
                            "WaterWolf": [{
                            "featured": true,
                            "throttle": 90.0,
                            "end_date": "%(end_date_19)s",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "19.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_19)s"
                            },
                            {
                            "featured": false,
                            "throttle": 33.333,
                            "end_date": "%(end_date_18)s",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "18.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_18)s"
                            },
                            {
                            "featured": true,
                            "throttle": 20.0,
                            "end_date": "%(end_date_17)s",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "17.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_17)s"
                            },
                            {
                            "featured": false,
                            "throttle": 20.0,
                            "end_date": "%(end_date_16)s",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "16.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_16)s"
                            }
                            ]
                        },
                        "total": 2
                    }
                """ % dates)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('19.0.1' in response.content)
        ok_('18.0.1' in response.content)
        # because its start_date is in the future
        ok_('17.0.1' not in response.content)
        # because its end_date is in the past
        ok_('17.0.1' not in response.content)

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
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
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

    def test_groups(self):
        url = reverse('manage:groups')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        wackos = Group.objects.create(name='Wackos')
        # Attach a known permission to it
        ct = ContentType.objects.create(
            model='',
            app_label='crashstats.crashstats',
        )
        Permission.objects.create(
            name='Mess Around',
            codename='mess_around',
            content_type=ct
        )
        wackos.permissions.add(
            Permission.objects.get(codename='mess_around')
        )
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

        # delete it
        response = self.client.post(url, {'delete': group.pk})
        eq_(response.status_code, 302)
        ok_(not Group.objects.filter(name=data['name']))

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

    @mock.patch('requests.get')
    def test_graphics_devices_lookup(self, rget):
        self._login()
        url = reverse('manage:graphics_devices_lookup')

        def mocked_get(url, params, **options):
            assert '/graphics_devices' in url
            if (
                'adapter_hex' in params and params['adapter_hex'] == 'xyz123'
                and 'vendor_hex' in params and params['vendor_hex'] == 'abc123'
            ):
                return Response("""
                {
                    "hits": [{
                        "vendor_hex": "abc123",
                        "adapter_hex": "xyz123",
                        "vendor_name": "Logictech",
                        "adapter_name": "Webcamera"
                    }],
                    "total": 1
                }
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

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

    @mock.patch('requests.post')
    def test_graphics_devices_edit(self, rpost):
        self._login()
        url = reverse('manage:graphics_devices')

        def mocked_post(url, **options):
            assert '/graphics_devices' in url
            data = options['data']
            data = json.loads(data)
            eq_(
                data[0],
                {
                    'vendor_hex': 'abc123',
                    'adapter_hex': 'xyz123',
                    'vendor_name': 'Logictech',
                    'adapter_name': 'Webcamera'
                }
            )
            return Response('true')

        rpost.side_effect = mocked_post

        response = self.client.post(url, {
            'vendor_hex': 'abc123',
            'adapter_hex': 'xyz123',
            'vendor_name': 'Logictech',
            'adapter_name': 'Webcamera'
        })
        eq_(response.status_code, 302)
        ok_(url in response['location'])

    @mock.patch('requests.post')
    def test_graphics_devices_csv_upload(self, rpost):
        self._login()
        url = reverse('manage:graphics_devices')

        def mocked_post(url, **options):
            assert '/graphics_devices' in url
            data = options['data']
            data = json.loads(data)
            eq_(
                data[0],
                {
                    'vendor_hex': '0x33',
                    'adapter_hex': '0x2f',
                    'vendor_name': 'Paradyne Corp.',
                    'adapter_name': '.43 ieee 1394 controller'
                }
            )
            eq_(len(data), 6)
            return Response('true')

        rpost.side_effect = mocked_post

        sample_file = os.path.join(
            os.path.dirname(__file__),
            'sample-graphics.csv'
        )
        with open(sample_file) as fp:
            response = self.client.post(url, {
                'file': fp
            })
            eq_(response.status_code, 302)
            ok_(url in response['location'])

    def test_symbols_uploads(self):
        self._login()
        url = reverse('manage:symbols_uploads')

        user = User.objects.create(username='user', email='user@mozilla.com')
        SymbolsUpload.objects.create(
            user=user,
            filename='file.zip',
            size=123456,
            content='Some Content'
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('file.zip' in response.content)
        ok_('user@mozilla.com' in response.content)

    @mock.patch('requests.get')
    def test_supersearch_fields(self, rget):
        self._login()
        url = reverse('manage:supersearch_fields')

        def mocked_get(url, **options):
            assert '/supersearch/fields/' in url

            return Response({
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
            })

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('signature' in response.content)
        ok_('string' in response.content)
        ok_('product' in response.content)
        ok_('enum' in response.content)

    @mock.patch('requests.get')
    def test_supersearch_fields_missing(self, rget):
        self._login()
        url = reverse('manage:supersearch_fields_missing')

        def mocked_get(url, **options):
            assert '/supersearch/' in url

            if '/supersearch/fields/' in url:
                return Response({
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
                })

            if '/supersearch/missing_fields/' in url:
                return Response({
                    'hits': [
                        'field_a',
                        'namespace1.field_b',
                        'namespace2.subspace1.field_c',
                    ],
                    'total': 3
                })

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('field_a' in response.content)
        ok_('namespace1.field_b' in response.content)
        ok_('namespace2.subspace1.field_c' in response.content)

    @mock.patch('requests.get')
    def test_supersearch_field(self, rget):
        self._login()
        url = reverse('manage:supersearch_field')

        def mocked_get(url, **options):
            assert '/supersearch/fields/' in url

            return Response({
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
            })

        rget.side_effect = mocked_get

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

    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_supersearch_field_create(self, rpost, rget):
        self._login()
        url = reverse('manage:supersearch_field_create')

        def mocked_get(url, **options):
            assert '/supersearch/fields/' in url
            return Response({})

        def mocked_post(url, data, **options):
            assert '/supersearch/field/' in url
            assert 'name' in data
            assert 'in_database_name' in data

            return Response(True)

        rget.side_effect = mocked_get
        rpost.side_effect = mocked_post

        response = self.client.post(
            url,
            {
                'name': 'something',
                'in_database_name': 'something',
            }
        )
        eq_(response.status_code, 302)

        response = self.client.post(url)
        eq_(response.status_code, 400)

        response = self.client.post(url, {'name': 'abcd'})
        eq_(response.status_code, 400)

        response = self.client.post(url, {'in_database_name': 'bar'})
        eq_(response.status_code, 400)

    @mock.patch('requests.get')
    @mock.patch('requests.put')
    def test_supersearch_field_update(self, rput, rget):
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

        def mocked_get(url, **options):
            assert '/supersearch/fields/' in url
            return Response({})

        def mocked_put(url, data, **options):
            assert '/supersearch/field/' in url

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

            return Response(True)

        rget.side_effect = mocked_get
        rput.side_effect = mocked_put

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

        response = self.client.post(url)
        eq_(response.status_code, 400)

        response = self.client.post(url, {'name': 'foo'})
        eq_(response.status_code, 400)

        response = self.client.post(url, {'in_database_name': 'bar'})
        eq_(response.status_code, 400)

    @mock.patch('requests.get')
    @mock.patch('requests.delete')
    def test_supersearch_field_delete(self, rdelete, rget):
        self._login()
        url = reverse('manage:supersearch_field_delete')

        def mocked_get(url, **options):
            assert '/supersearch/fields/' in url
            return Response({})

        def mocked_delete(url, params, **options):
            assert '/supersearch/field/' in url
            assert 'name' in params

            return Response(True)

        rget.side_effect = mocked_get
        rdelete.side_effect = mocked_delete

        response = self.client.get(url, {'name': 'signature'})
        eq_(response.status_code, 302)

        response = self.client.get(url)
        eq_(response.status_code, 400)
