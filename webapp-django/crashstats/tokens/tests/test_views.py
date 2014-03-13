import pyquery
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission, Group

from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.tokens import models


class TestViews(BaseTestViews):

    def _login(self):
        user = User.objects.create_user('test', 'test@mozilla.com', 'secret')
        assert self.client.login(username='test', password='secret')
        return user

    def _make_permission(self, name, codename=None):
        codename = codename or name.lower().replace(' ', '-')
        ct, __ = ContentType.objects.get_or_create(
            model='',
            app_label='crashstats',
        )
        return Permission.objects.create(
            name=name,
            codename=codename,
            content_type=ct
        )

    def test_home_page(self):
        url = reverse('tokens:home')
        response = self.client.get(url)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_generate_new_token_form(self):
        url = reverse('tokens:home')
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # which choices you have depend in your owned permissions
        doc = pyquery.PyQuery(response.content)
        eq_(len(doc('#id_permissions')), 0)

        p1 = self._make_permission('Make a mess', 'make-mess')
        p2 = self._make_permission('Clean Things', 'cool-things')
        p3 = self._make_permission('Play with sticks', 'play-with-sticks')
        group = Group.objects.create(name='Cool people')
        group.permissions.add(p1)
        group.permissions.add(p3)
        user.groups.add(group)

        assert user.has_perm('crashstats.%s' % p1.codename)
        assert not user.has_perm('crashstats.%s' % p2.codename)
        assert user.has_perm('crashstats.%s' % p3.codename)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        # which choices you have depend in your owned permissions
        doc = pyquery.PyQuery(response.content)
        eq_(len(doc('#id_permissions option')), 2)

    def test_generate_new_token(self):
        url = reverse('tokens:home')
        p1 = self._make_permission('Make a mess')
        self._make_permission('Clean Things')
        p3 = self._make_permission('Play with sticks')

        response = self.client.post(url, {
            'notes': ' Some notes ',
            'permissions': [p1.pk, p3.pk]
        })
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )

        # try again, but this time logged in
        user = self._login()
        response = self.client.post(url, {
            'notes': ' Some notes ',
            'permissions': [p1.pk, p3.pk]
        })
        # because you tried to assign this token permissions you
        # don't have
        eq_(response.status_code, 403)

        #
        group = Group.objects.create(name='Cool people')
        group.permissions.add(p1)
        group.permissions.add(p3)
        user.groups.add(group)

        response = self.client.post(url, {
            'notes': ' Some notes ',
            'permissions': [p1.pk, p3.pk]
        })
        # because you tried to assign this token permissions you
        # don't have
        eq_(response.status_code, 302)

        token, = models.Token.objects.active().filter(user=user)
        eq_(set(token.permissions.all()), set([p1, p3]))

        # this should be listed on the home page now
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # because the `token.key` is shown in a split way...
        ok_(token.key not in response.content)
        # but some of it is
        ok_(token.key[:12] in response.content)

    def test_delete_token(self):
        user = self._login()
        token1 = models.Token.objects.create(
            user=user,
            notes='Some note'
        )
        other_user = User.objects.create(username='else')
        token_other_user = models.Token.objects.create(
            user=other_user,
        )

        url = reverse('tokens:delete_token', args=(token1.pk,))
        response = self.client.post(url)
        eq_(response.status_code, 302)
        ok_(not models.Token.objects.filter(notes='Some note'))

        # but you can't delete someone elses
        url = reverse('tokens:delete_token', args=(token_other_user.pk,))
        response = self.client.post(url)
        eq_(response.status_code, 404)
