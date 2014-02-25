from django.conf import settings
from django.utils.functional import wraps

from mock import patch

### From Mozillians


class MockedResponse(object):
    def __init__(self, response):
        self.response = response

    def json(self):
        return self.response


class mock_browserid(object):
    def __init__(self, email=None):
        self.settings_patches = (
            patch.object(
                settings, 'AUTHENTICATION_BACKENDS',
                ('django_browserid.auth.BrowserIDBackend',),
            ),
            patch.object(
                settings, 'BROWSERID_AUDIENCES',
                ['http://testserver'],
            )
        )
        self.patcher = patch('django_browserid.base.requests.post')
        if email is not None:
            self.return_value = MockedResponse(
                {'status': 'okay', 'email': email}
            )
        else:
            self.return_value = MockedResponse(
                {'status': 'failure'}
            )

    def __enter__(self):
        for patch in self.settings_patches:
            patch.start()
        self.patcher.start().return_value = self.return_value

    def __exit__(self, exc_type, exc_value, traceback):
        for patch in self.settings_patches:
            patch.stop()
        self.patcher.stop()

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return inner
