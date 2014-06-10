import os
import shutil
import tempfile

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.core.files import File

from crashstats.tokens.models import Token
from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.symbols import models


from .base import ZIP_FILE, TARGZ_FILE, TGZ_FILE, TAR_FILE


class EmptyFile(object):

    def __init__(self, name):
        self.name = name

    def read(self):
        return ''

    def size(self):
        return 0


class TestViews(BaseTestViews):

    def setUp(self):
        super(TestViews, self).setUp()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(TestViews, self).tearDown()
        shutil.rmtree(self.tmp_dir)

    def _login(self):
        user = User.objects.create_user('test', 'test@mozilla.com', 'secret')
        assert self.client.login(username='test', password='secret')
        return user

    def test_home(self):
        self._create_group_with_permission('upload_symbols')
        url = reverse('symbols:home')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )
        self._login()
        with self.settings(SYMBOLS_PERMISSION_HINT_LINK=None):
            response = self.client.get(url)
            eq_(response.status_code, 200)

        link = {
            'url': 'https://bugzilla.mozilla.org',
            'label': 'Bugzilla'
        }
        with self.settings(SYMBOLS_PERMISSION_HINT_LINK=link):
            response = self.client.get(url)
            eq_(response.status_code, 200)

            ok_(link['url'] in response.content)
            ok_(link['label'] in response.content)

    def test_home_with_previous_uploads(self):
        url = reverse('symbols:home')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        upload1 = models.SymbolsUpload.objects.create(
            user=user,
            content='file1\nfile2',
            filename='file1.zip',
            size=12345
        )
        upload2 = models.SymbolsUpload.objects.create(
            user=user,
            content='file1\nfile2',
            filename='sample.zip',
            size=10000
        )
        with open(ZIP_FILE) as f:
            upload2.file.save('sample.zip', File(f))

        response = self.client.get(url)
        eq_(response.status_code, 200)
        # note that the file for upload1 does not exist
        ok_(
            reverse('symbols:download', args=(upload1.pk,))
            not in response.content
        )
        # but you can for upload 2
        ok_(
            reverse('symbols:download', args=(upload2.pk,))
            in response.content
        )
        # but you can preview both
        ok_(
            reverse('symbols:preview', args=(upload1.pk,))
            in response.content
        )
        ok_(
            reverse('symbols:preview', args=(upload2.pk,))
            in response.content
        )

    def test_web_upload(self):
        url = reverse('symbols:web_upload')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )
        # you need to have the permission
        self._add_permission(user, 'upload_symbols')

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # now we can post
        with self.settings(MEDIA_ROOT=self.tmp_dir):
            with open(ZIP_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file': file_object}
                )
                eq_(response.status_code, 302)

            symbol_upload = models.SymbolsUpload.objects.get(user=user)
            eq_(symbol_upload.filename, os.path.basename(ZIP_FILE))
            ok_(symbol_upload.size)
            ok_(symbol_upload.file)
            ok_(symbol_upload.file_exists)
            ok_(symbol_upload.content)

    def test_web_upload_tar_gz_file(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        # now we can post
        with self.settings(MEDIA_ROOT=self.tmp_dir):
            with open(TARGZ_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file': file_object}
                )
                eq_(response.status_code, 302)

            symbol_upload = models.SymbolsUpload.objects.get(user=user)
            eq_(symbol_upload.filename, os.path.basename(TARGZ_FILE))
            ok_(symbol_upload.size)
            ok_(symbol_upload.file)
            ok_(symbol_upload.file_exists)
            ok_(symbol_upload.content)

    def test_web_upload_tgz_file(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        # now we can post
        with self.settings(MEDIA_ROOT=self.tmp_dir):
            with open(TGZ_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file': file_object}
                )
                eq_(response.status_code, 302)

            symbol_upload = models.SymbolsUpload.objects.get(user=user)
            eq_(symbol_upload.filename, os.path.basename(TGZ_FILE))
            ok_(symbol_upload.size)
            ok_(symbol_upload.file)
            ok_(symbol_upload.file_exists)
            ok_(symbol_upload.content)

    def test_web_upload_tar_file(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        # now we can post
        with self.settings(MEDIA_ROOT=self.tmp_dir):
            with open(TAR_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file': file_object}
                )
                eq_(response.status_code, 302)

            symbol_upload = models.SymbolsUpload.objects.get(user=user)
            eq_(symbol_upload.filename, os.path.basename(TAR_FILE))
            ok_(symbol_upload.size)
            ok_(symbol_upload.file)
            ok_(symbol_upload.file_exists)
            ok_(symbol_upload.content)

    def test_api_upload_about(self):
        url = reverse('symbols:api_upload')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )
        self._add_permission(user, 'upload_symbols')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('you need to generate' in response.content)

        token = Token.objects.create(
            user=user,
        )
        token.permissions.add(
            Permission.objects.get(codename='upload_symbols')
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('you need to generate' not in response.content)

    def test_upload(self):
        user = User.objects.create(username='user')
        self._add_permission(user, 'upload_symbols')
        token = Token.objects.create(
            user=user,
        )
        token.permissions.add(
            Permission.objects.get(codename='upload_symbols')
        )

        url = reverse('symbols:upload')
        response = self.client.get(url)
        eq_(response.status_code, 405)

        with self.settings(MEDIA_ROOT=self.tmp_dir):
            with open(ZIP_FILE, 'rb') as file_object:
                response = self.client.post(
                    url,
                    {'file.zip': file_object},
                    HTTP_AUTH_TOKEN=token.key
                )
            eq_(response.status_code, 201)
            symbol_upload = models.SymbolsUpload.objects.get(user=user)
            eq_(symbol_upload.filename, 'file.zip')
            ok_(symbol_upload.size)
            ok_(symbol_upload.file)
            ok_(symbol_upload.file_exists)
            ok_(symbol_upload.content)

    def test_upload_empty_file(self):
        user = User.objects.create(username='user')
        self._add_permission(user, 'upload_symbols')
        token = Token.objects.create(
            user=user,
        )
        token.permissions.add(
            Permission.objects.get(codename='upload_symbols')
        )

        url = reverse('symbols:upload')
        response = self.client.get(url)
        eq_(response.status_code, 405)

        with self.settings(MEDIA_ROOT=self.tmp_dir):
            response = self.client.post(
                url,
                {'file.zip': EmptyFile('file.zip')},
                HTTP_AUTH_TOKEN=token.key
            )
        eq_(response.status_code, 400)

    def test_download(self):
        user = User.objects.create_user('test', 'test@mozilla.com', 'secret')

        with self.settings(MEDIA_ROOT=self.tmp_dir):
            with open(ZIP_FILE, 'rb') as file_object:
                upload = models.SymbolsUpload.objects.create(
                    user=user,
                    file=File(file_object),
                    filename=os.path.basename(ZIP_FILE),
                    size=12345,
                    content='Content'
                )

            url = reverse('symbols:download', args=(upload.pk,))
            response = self.client.get(url)
            eq_(response.status_code, 302)
            self.assertRedirects(
                response,
                reverse('crashstats:login') + '?next=%s' % url
            )
            assert self.client.login(username='test', password='secret')
            response = self.client.get(url)
            eq_(response.status_code, 200)
            eq_(response['Content-Type'], 'application/zip')
            eq_(
                response['Content-Disposition'],
                'attachment; filename="sample.zip"'
            )

            # log in as someone else
            user = User.objects.create_user(
                'else', 'else@mozilla.com', 'secret'
            )
            assert self.client.login(username='else', password='secret')
            response = self.client.get(url)
            eq_(response.status_code, 403)

            user.is_superuser = True
            user.save()
            assert self.client.login(username='else', password='secret')
            response = self.client.get(url)
            eq_(response.status_code, 200)

    def test_preview(self):
        user = User.objects.create_user('test', 'test@mozilla.com', 'secret')

        with self.settings(MEDIA_ROOT=self.tmp_dir):
            with open(ZIP_FILE, 'rb') as file_object:
                upload = models.SymbolsUpload.objects.create(
                    user=user,
                    file=File(file_object),
                    filename=os.path.basename(ZIP_FILE),
                    size=12345,
                    content='Content'
                )

            url = reverse('symbols:preview', args=(upload.pk,))
            response = self.client.get(url)
            eq_(response.status_code, 302)
            self.assertRedirects(
                response,
                reverse('crashstats:login') + '?next=%s' % url
            )
            assert self.client.login(username='test', password='secret')
            response = self.client.get(url)
            eq_(response.status_code, 200)
            eq_(response.content, 'Content')
            eq_(response['Content-Type'], 'text/plain')

            # log in as someone else
            user = User.objects.create_user(
                'else', 'else@mozilla.com', 'secret'
            )
            assert self.client.login(username='else', password='secret')
            response = self.client.get(url)
            eq_(response.status_code, 403)

            user.is_superuser = True
            user.save()
            assert self.client.login(username='else', password='secret')
            response = self.client.get(url)
            eq_(response.status_code, 200)
