import json

from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.utils import timezone

from crashstats.tokens.models import Token
from crashstats.symbols.models import SymbolsUpload
from crashstats.crashstats.tests.test_views import BaseTestViews


class TestAPI(BaseTestViews):

    def test_empty_get(self):
        url = reverse('api:model_wrapper', args=('UploadedSymbols',))

        response = self.client.get(url)
        assert response.status_code == 403
        assert 'requires' in response.content
        assert 'View all Symbol Uploads' in response.content

        # create a user, who has this permission
        perm = Permission.objects.get(name='View all Symbol Uploads')
        assert perm.codename == 'view_all_symbol_uploads'
        user = User.objects.create_user('bob', 'bob@example.com', 'secret')

        token = Token.objects.create(user=user)
        token.permissions.add(perm)

        response = self.client.get(url, HTTP_AUTH_TOKEN=token.key)
        assert response.status_code == 400

        # we're missing required params
        today = timezone.now()
        params = {
            'start_date': today.date(),
            'end_date': today.date(),
        }
        response = self.client.get(url, params, HTTP_AUTH_TOKEN=token.key)
        assert response.status_code == 200
        results = json.loads(response.content)
        assert results['total'] == 0
        assert results['hits'] == []

    def test_search_by_params(self):
        url = reverse('api:model_wrapper', args=('UploadedSymbols',))

        user = self._login()
        self._add_permission(user, 'view_all_symbol_uploads')
        today = timezone.now()

        upload = SymbolsUpload.objects.create(
            user=user,
            filename='symbolics.zip',
            size=1234,
            content_type='application/zip',
            content=(
                "+somebucket,file1.sym\n"
                "=somebucket,file2.sym\n"
            )
        )
        params = {
            'start_date': today.date(),
            'end_date': today.date(),
        }
        response = self.client.get(url, params)
        assert response.status_code == 200
        results = json.loads(response.content)
        assert results['total'] == 1
        expect = {
            'id': upload.id,
            'filename': 'symbolics.zip',
            'content': {
                'existed': ['somebucket,file2.sym'],
                'added': ['somebucket,file1.sym'],
            },
            'user': user.email,
            'date': upload.created.isoformat(),
            'size': 1234,
            'content_type': 'application/zip',
        }
        assert results['hits'] == [expect]

        # Ok, basics work, now try to filter by something more advanced
        response = self.client.get(url, dict(params, user_search='xxx'))
        assert response.status_code == 200
        results = json.loads(response.content)
        assert results['total'] == 0

        assert user.email == 'test@example.com', user.email
        response = self.client.get(url, dict(params, user_search='TEST'))
        assert response.status_code == 200
        results = json.loads(response.content)
        assert results['total'] == 1

        response = self.client.get(url, dict(params, filename_search='xxx'))
        assert response.status_code == 200
        results = json.loads(response.content)
        assert results['total'] == 0
        response = self.client.get(url, dict(params, filename_search='bolic'))
        assert response.status_code == 200
        results = json.loads(response.content)
        assert results['total'] == 1

        response = self.client.get(url, dict(params, content_search='xxx'))
        assert response.status_code == 200
        results = json.loads(response.content)
        assert results['total'] == 0
        response = self.client.get(url, dict(params, content_search='file1'))
        assert response.status_code == 200
        results = json.loads(response.content)
        assert results['total'] == 1
