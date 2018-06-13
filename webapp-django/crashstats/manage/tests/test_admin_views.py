from django.core.urlresolvers import reverse

from crashstats.crashstats.tests.test_views import BaseTestViews

import pytest


class TestCrashMeNow(BaseTestViews):
    def _login(self, is_superuser=True):
        user = super(TestCrashMeNow, self)._login(
            username='lonnen',
            email='lonnen@example.com',
        )
        user.is_superuser = is_superuser
        user.is_staff = is_superuser
        user.save()
        return user

    def test_view(self):
        url = reverse('siteadmin:crash_me_now')
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        with pytest.raises(ZeroDivisionError):
            self.client.get(url)
