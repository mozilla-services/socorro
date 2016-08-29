import os
import shutil
import tempfile

from nose.tools import eq_, ok_, assert_raises
import mock

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

from crashstats.tokens.models import Token
from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.symbols import models
from crashstats.symbols.views import check_symbols_archive_content

from .base import (
    ZIP_FILE,
    TARGZ_FILE,
    TGZ_FILE,
    TAR_FILE,
    ACTUALLY_NOT_ZIP_FILE,
)
from crashstats.symbols.views import (
    unpack_and_upload,
    get_bucket_name_and_location,
)


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

        self.patcher = mock.patch('crashstats.symbols.views.boto.connect_s3')
        self.uploaded_keys = {}
        self.uploaded_headers = {}
        self.known_bucket_keys = {}
        self.created_buckets = []
        self.created_keys = []
        mocked_connect_s3 = self.patcher.start()

        self.symbols_compress_extensions = settings.SYMBOLS_COMPRESS_EXTENSIONS
        # Forcibly set this for all tests so it doesn't matter what's in
        # settings/base.py or any local overrides
        settings.SYMBOLS_COMPRESS_EXTENSIONS = ('sym',)

        def mocked_lookup(*a, **k):
            return None

        def mocked_create_bucket(name, location):

            def mocked_new_key(key_name):
                mocked_key = mock.Mock()

                def mocked_set(string, headers=None):
                    self.uploaded_keys[key_name] = string
                    self.uploaded_headers[key_name] = headers
                    return len(string)

                mocked_key.set_contents_from_string.side_effect = mocked_set
                mocked_key.key = key_name
                mocked_key.bucket = mocked_bucket
                self.created_keys.append(mocked_key)
                return mocked_key

            def mocked_get_key(key_name):
                # return None there is no known fixture by this name
                if key_name in self.known_bucket_keys:
                    mocked_key = mock.Mock()
                    mocked_key.key = key_name
                    mocked_key.content_type = 'application/binary-octet-stream'
                    mocked_key.size = self.known_bucket_keys[key_name]
                    mocked_key.bucket = mocked_bucket
                    return mocked_key
                return None

            mocked_bucket = mock.Mock()
            mocked_bucket.name = name
            self.created_buckets.append((name, location))
            mocked_bucket.new_key.side_effect = mocked_new_key
            mocked_bucket.get_key.side_effect = mocked_get_key
            return mocked_bucket

        mocked_connect_s3().lookup = mocked_lookup
        mocked_connect_s3().create_bucket = mocked_create_bucket

    def tearDown(self):
        super(TestViews, self).tearDown()
        shutil.rmtree(self.tmp_dir)
        self.patcher.stop()
        settings.SYMBOLS_COMPRESS_EXTENSIONS = self.symbols_compress_extensions

    def test_unpack_and_upload_misconfigured(self):
        with self.settings(AWS_ACCESS_KEY=''):
            assert_raises(
                ImproperlyConfigured,
                unpack_and_upload,
                [],
                None,
                'some-name',
                None
            )

    def test_check_symbols_archive_content(self):
        content = """
        Line 1
        Line Two
        Line Three
        """

        # match something
        disallowed = ('Two', '2')
        with self.settings(DISALLOWED_SYMBOLS_SNIPPETS=disallowed):
            error = check_symbols_archive_content(content.strip())
            ok_(error)
            ok_('Two' in error)

        # match nothing
        disallowed = ('evil', 'Bad')
        with self.settings(DISALLOWED_SYMBOLS_SNIPPETS=disallowed):
            error = check_symbols_archive_content(content.strip())
            ok_(not error)

    def test_home(self):
        self._create_group_with_permission('upload_symbols')
        url = reverse('symbols:home')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )
        user = self._login()
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

        # The access should disappear if you cease to be active
        user.is_active = False
        user.save()
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('crashstats:login') + '?next=%s' % url
        )

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

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(
            reverse('symbols:content', args=(upload1.pk,))
            in response.content
        )
        ok_(
            reverse('symbols:content', args=(upload2.pk,))
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
        with self.settings(SYMBOLS_MIME_OVERRIDES={'jpeg': 'text/plain'}):
            with open(ZIP_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file': file_object}
                )
                eq_(response.status_code, 302)

        symbol_upload = models.SymbolsUpload.objects.get(user=user)
        eq_(symbol_upload.filename, os.path.basename(ZIP_FILE))
        ok_(symbol_upload.size)
        # We expect the content to be a `+` because it was new,
        # followed by the bucket name, followed by a comma, followed
        # by the symbols prefix + filename.
        line = "+%s,%s/%s\n" % (
            settings.SYMBOLS_BUCKET_DEFAULT_NAME,
            settings.SYMBOLS_FILE_PREFIX,
            'south-africa-flag.jpeg'
        )
        line += "+%s,%s/%s\n" % (
            settings.SYMBOLS_BUCKET_DEFAULT_NAME,
            settings.SYMBOLS_FILE_PREFIX,
            'xpcshell.sym'
        )
        eq_(symbol_upload.content, line)
        eq_(symbol_upload.content_type, 'text/plain')
        ok_(self.uploaded_keys)
        # the mocked key object should have its content_type set too
        eq_(self.created_keys[0].content_type, 'text/plain')
        eq_(self.created_buckets, [
            (
                settings.SYMBOLS_BUCKET_DEFAULT_NAME,
                settings.SYMBOLS_BUCKET_DEFAULT_LOCATION
            )
        ])

    def test_web_upload_different_bucket_by_wildcard(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')
        assert user.email.endswith('@mozilla.com')
        exception_names = {
            '*@mozilla.com': 'my-special-bucket-name',
            '*@example.com': 'other-bucket-name',
        }
        with self.settings(SYMBOLS_BUCKET_EXCEPTIONS=exception_names):
            with open(ZIP_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file': file_object}
                )
                eq_(response.status_code, 302)

            symbol_upload = models.SymbolsUpload.objects.get(user=user)
            eq_(symbol_upload.filename, os.path.basename(ZIP_FILE))
            ok_(symbol_upload.size)
            line = "+%s,%s/%s\n" % (
                'my-special-bucket-name',
                settings.SYMBOLS_FILE_PREFIX,
                'south-africa-flag.jpeg'
            )
            line += "+%s,%s/%s\n" % (
                'my-special-bucket-name',
                settings.SYMBOLS_FILE_PREFIX,
                'xpcshell.sym'
            )
            eq_(symbol_upload.content, line)
            eq_(self.created_buckets, [
                (
                    'my-special-bucket-name',
                    settings.SYMBOLS_BUCKET_DEFAULT_LOCATION
                )
            ])

    def test_get_bucket_name_and_location(self):

        class _User(object):
            def __init__(self, email):
                self.email = email

        # no exceptions set
        result = get_bucket_name_and_location(
            _User('user@example.com')
        )
        eq_(
            result,
            (
                settings.SYMBOLS_BUCKET_DEFAULT_NAME,
                settings.SYMBOLS_BUCKET_DEFAULT_LOCATION
            )
        )

        exceptions = {'user@example.com': 'my-bucket'}
        with self.settings(SYMBOLS_BUCKET_EXCEPTIONS=exceptions):
            # a good regular match
            result = get_bucket_name_and_location(
                _User('user@example.com')
            )
            eq_(result[0], 'my-bucket')

            # a failing match
            result = get_bucket_name_and_location(
                _User('other_user@example.com')
            )
            eq_(result[0], settings.SYMBOLS_BUCKET_DEFAULT_NAME)

            # a case insensitive match
            result = get_bucket_name_and_location(
                _User('UsEr@example.COM')
            )
            eq_(result[0], 'my-bucket')

        # now with wildcards
        exceptions = {'*@example.com': 'my-bucket'}
        with self.settings(SYMBOLS_BUCKET_EXCEPTIONS=exceptions):
            # a good match
            result = get_bucket_name_and_location(
                _User('user@example.com')
            )
            eq_(result[0], 'my-bucket')

            # a failing match
            result = get_bucket_name_and_location(
                _User('user@example.biz')
            )
            eq_(result[0], settings.SYMBOLS_BUCKET_DEFAULT_NAME)

            # a case insensitive match
            result = get_bucket_name_and_location(
                _User('UsEr@example.COM')
            )
            eq_(result[0], 'my-bucket')

        # now with wildcards inside the email
        exceptions = {'start*@example.com': 'my-bucket'}
        with self.settings(SYMBOLS_BUCKET_EXCEPTIONS=exceptions):
            # a failing match
            result = get_bucket_name_and_location(
                _User('user@example.com')
            )
            eq_(result[0], settings.SYMBOLS_BUCKET_DEFAULT_NAME)

            # a failing match containing 'start'
            result = get_bucket_name_and_location(
                _User('notstarting@example.com')
            )
            eq_(result[0], settings.SYMBOLS_BUCKET_DEFAULT_NAME)

            # a good match and case insensitive
            result = get_bucket_name_and_location(
                _User('STARter@example.COM')
            )
            eq_(result[0], 'my-bucket')

    def test_web_upload_different_bucket_by_user_different_location(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')
        exception_names = {
            user.email: 'my-special-bucket-name|us-north-1',
        }
        with self.settings(SYMBOLS_BUCKET_EXCEPTIONS=exception_names):
            with open(ZIP_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file': file_object}
                )
                eq_(response.status_code, 302)

            symbol_upload = models.SymbolsUpload.objects.get(user=user)
            eq_(symbol_upload.filename, os.path.basename(ZIP_FILE))
            ok_(symbol_upload.size)
            line = "+%s,%s/%s\n" % (
                'my-special-bucket-name',
                settings.SYMBOLS_FILE_PREFIX,
                'south-africa-flag.jpeg'
            )
            line += "+%s,%s/%s\n" % (
                'my-special-bucket-name',
                settings.SYMBOLS_FILE_PREFIX,
                'xpcshell.sym'
            )
            eq_(symbol_upload.content, line)
            eq_(self.created_buckets, [
                (
                    'my-special-bucket-name',
                    'us-north-1'
                )
            ])

    def test_upload_different_bucket_by_user_different_location(self):
        url = reverse('symbols:upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')
        token = Token.objects.create(
            user=user,
        )
        token.permissions.add(
            Permission.objects.get(codename='upload_symbols')
        )

        exception_names = {
            user.email: 'my-special-bucket-name|us-north-1',
        }
        with self.settings(SYMBOLS_BUCKET_EXCEPTIONS=exception_names):
            with open(ZIP_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file.zip': file_object},
                    HTTP_AUTH_TOKEN=token.key
                )
                eq_(response.status_code, 201)

            symbol_upload = models.SymbolsUpload.objects.get(user=user)
            eq_(symbol_upload.filename, 'file.zip')
            line = "+%s,%s/%s\n" % (
                'my-special-bucket-name',
                settings.SYMBOLS_FILE_PREFIX,
                'south-africa-flag.jpeg'
            )
            line += "+%s,%s/%s\n" % (
                'my-special-bucket-name',
                settings.SYMBOLS_FILE_PREFIX,
                'xpcshell.sym'
            )
            eq_(symbol_upload.content, line)
            eq_(self.created_buckets, [
                (
                    'my-special-bucket-name',
                    'us-north-1'
                )
            ])

    def test_web_upload_existing_upload(self):
        """what if the file already is uploaded"""
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        # We know the size of the file `south-africa-flag.jpeg` inside the
        # fixture ZIP_FILE is 69183
        key_name = '%s/south-africa-flag.jpeg' % settings.SYMBOLS_FILE_PREFIX
        self.known_bucket_keys[key_name] = 69183

        with open(ZIP_FILE) as file_object:
            response = self.client.post(
                url,
                {'file': file_object}
            )
            eq_(response.status_code, 302)
        symbol_upload = models.SymbolsUpload.objects.get(user=user)
        # Now we expect it to be a prefixed with a `=` because it's not
        # new and thus didn't cause an upload.
        line = "=%s,%s/%s\n" % (
            settings.SYMBOLS_BUCKET_DEFAULT_NAME,
            settings.SYMBOLS_FILE_PREFIX,
            'south-africa-flag.jpeg'
        )
        line += "+%s,%s/%s\n" % (
            settings.SYMBOLS_BUCKET_DEFAULT_NAME,
            settings.SYMBOLS_FILE_PREFIX,
            'xpcshell.sym'
        )
        eq_(symbol_upload.content, line)
        # only the xpcshell.sym was uploaded
        eq_(
            self.uploaded_keys.keys(),
            ['%s/xpcshell.sym' % (settings.SYMBOLS_FILE_PREFIX,)]
        )

    def test_web_upload_existing_upload_but_different_size(self):
        """what if the file already is uploaded"""
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        # We know the size of the file `south-africa-flag.jpeg` inside the
        # fixture ZIP_FILE is 69183
        key_name = '%s/south-africa-flag.jpeg' % settings.SYMBOLS_FILE_PREFIX
        # deliberately different from 69183
        self.known_bucket_keys[key_name] = 1000

        with open(ZIP_FILE) as file_object:
            response = self.client.post(
                url,
                {'file': file_object}
            )
            eq_(response.status_code, 302)
        symbol_upload = models.SymbolsUpload.objects.get(user=user)
        # Now we expect it to be a prefixed with a `=` because it's not
        # new and thus didn't cause an upload.
        line = "+%s,%s/%s\n" % (
            settings.SYMBOLS_BUCKET_DEFAULT_NAME,
            settings.SYMBOLS_FILE_PREFIX,
            'south-africa-flag.jpeg'
        )
        line += "+%s,%s/%s\n" % (
            settings.SYMBOLS_BUCKET_DEFAULT_NAME,
            settings.SYMBOLS_FILE_PREFIX,
            'xpcshell.sym'
        )
        eq_(symbol_upload.content, line)
        ok_(key_name in self.uploaded_keys)

    def test_web_upload_disallowed_content(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')
        # because the file ZIP_FILE contains the word `south-africa-flag.jpeg`
        # it should not be allowed to be uploaded
        disallowed = ('flag',)
        with self.settings(MEDIA_ROOT=self.tmp_dir,
                           DISALLOWED_SYMBOLS_SNIPPETS=disallowed):
            with open(ZIP_FILE) as file_object:
                response = self.client.post(
                    url,
                    {'file': file_object}
                )
                eq_(response.status_code, 400)
                ok_('flag' in response.content)

    def test_web_upload_tar_gz_file(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        # now we can post
        with open(TARGZ_FILE) as file_object:
            response = self.client.post(
                url,
                {'file': file_object}
            )
            eq_(response.status_code, 302)

        symbol_upload = models.SymbolsUpload.objects.get(user=user)
        eq_(symbol_upload.filename, os.path.basename(TARGZ_FILE))
        ok_(symbol_upload.size)
        ok_(symbol_upload.content)

    def test_web_upload_tgz_file(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        # now we can post
        with open(TGZ_FILE) as file_object:
            response = self.client.post(
                url,
                {'file': file_object}
            )
            eq_(response.status_code, 302)

        symbol_upload = models.SymbolsUpload.objects.get(user=user)
        eq_(symbol_upload.filename, os.path.basename(TGZ_FILE))
        ok_(symbol_upload.size)
        ok_(symbol_upload.content)

    def test_web_upload_tar_file(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')

        # now we can post
        with open(TAR_FILE) as file_object:
            response = self.client.post(
                url,
                {'file': file_object}
            )
            eq_(response.status_code, 302)

        symbol_upload = models.SymbolsUpload.objects.get(user=user)
        eq_(symbol_upload.filename, os.path.basename(TAR_FILE))
        ok_(symbol_upload.size)
        ok_(symbol_upload.content)

        assert self.uploaded_keys

    def test_web_upload_unrecognized_file_extension(self):
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')
        with open(__file__) as file_object:
            response = self.client.post(
                url,
                {'file': file_object}
            )
            eq_(response.status_code, 200)
            ok_('Unrecognized file' in response.content)

        assert not models.SymbolsUpload.objects.all()
        assert not self.uploaded_keys

    def test_web_upload_fake_file_extension(self):
        """
        Let's try to upload a file that seems to be a .zip file by its
        name but isn't actually one.
        This will result in the unpacking causing an exception and we
        return that as a 400 Bad Request.
        This is basically the case of seeking forgiveness instead of
        asking for permission. I.e. we just try to unpack it if at least
        the file name extension is recognized.
        """
        url = reverse('symbols:web_upload')
        user = self._login()
        self._add_permission(user, 'upload_symbols')
        with open(ACTUALLY_NOT_ZIP_FILE) as file_object:
            response = self.client.post(
                url,
                {'file': file_object}
            )
            eq_(response.status_code, 400)
            ok_('File is not a zip file' in response.content)

        assert not models.SymbolsUpload.objects.all()
        assert not self.uploaded_keys

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
                    # note! No HTTP_AUTH_TOKEN
                )
                eq_(response.status_code, 403)

            with open(ZIP_FILE, 'rb') as file_object:
                response = self.client.post(
                    url,
                    {'file.zip': file_object},
                    HTTP_AUTH_TOKEN=''
                )
                eq_(response.status_code, 403)

            with open(ZIP_FILE, 'rb') as file_object:
                response = self.client.post(
                    url,
                    {'file.zip': file_object},
                    HTTP_AUTH_TOKEN='somejunk'
                )
                eq_(response.status_code, 403)

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
                ok_(symbol_upload.content)

        # the ZIP_FILE contains a file called south-africa-flag.jpeg
        key = os.path.join(
            settings.SYMBOLS_FILE_PREFIX,
            'south-africa-flag.jpeg'
        )
        ok_(self.uploaded_keys[key])
        eq_(self.uploaded_headers[key], {'Content-Type': 'image/jpeg'})

        # and a file called xpcshell.sym
        key = os.path.join(
            settings.SYMBOLS_FILE_PREFIX,
            'xpcshell.sym'
        )
        ok_(self.uploaded_keys[key])
        eq_(self.uploaded_headers[key], {
            'Content-Type': 'text/plain',
            'Content-Encoding': 'gzip'
        })
        # The sample.zip file contains the file xpcshell.sym and it's
        # 1156 bytes when un-archived. Just gzip'in the content of the
        # file will yield a file that is 476 bytes.
        # But if you do it properly there's header information in the
        # string which is a couple of extra bytes.
        eq_(len(self.uploaded_keys[key]), 488)

    def test_upload_without_multipart_file(self):
        user = User.objects.create(username='user')
        self._add_permission(user, 'upload_symbols')
        token = Token.objects.create(
            user=user,
        )
        token.permissions.add(
            Permission.objects.get(codename='upload_symbols')
        )

        url = reverse('symbols:upload')
        response = self.client.post(url, HTTP_AUTH_TOKEN=token.key)
        eq_(response.status_code, 400)

    def test_upload_disallowed_content(self):
        user = User.objects.create(username='user')
        self._add_permission(user, 'upload_symbols')
        token = Token.objects.create(
            user=user,
        )
        token.permissions.add(
            Permission.objects.get(codename='upload_symbols')
        )

        url = reverse('symbols:upload')
        # because the file ZIP_FILE contains the word `south-africa-flag.jpeg`
        # it should not be allowed to be uploaded
        disallowed = ('flag',)
        with self.settings(DISALLOWED_SYMBOLS_SNIPPETS=disallowed):
            with open(ZIP_FILE, 'rb') as file_object:
                response = self.client.post(
                    url,
                    {'file.zip': file_object},
                    HTTP_AUTH_TOKEN=token.key
                )
            eq_(response.status_code, 400)
            ok_('flag' in response.content)

        # nothing should have been sent to S3
        ok_(not self.uploaded_keys)

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

        # nothing should have been sent to S3
        ok_(not self.uploaded_keys)

    def test_preview(self):
        user = User.objects.create_user('test', 'test@mozilla.com', 'secret')

        upload = models.SymbolsUpload.objects.create(
            user=user,
            filename=os.path.basename(ZIP_FILE),
            size=12345,
            content='Content'
        )

        url = reverse('symbols:content', args=(upload.pk,))
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
