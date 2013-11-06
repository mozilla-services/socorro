from django.conf import settings
from django.core.urlresolvers import reverse

from django_browserid.views import Verify


class CustomBrowserIDVerify(Verify):

    @property
    def failure_url(self):
        # if we don't do this, upon failure it might redirect
        # to `/?bid_login_failed=1` which will redirect to
        # `/home/products/:defaultproduct` without the `?bid_login_failed=1`
        # part which doesn't tell browserID that it went wrong
        return reverse('crashstats.home', args=(settings.DEFAULT_PRODUCT,))

    @property
    def success_url(self):
        return reverse('crashstats.home', args=(settings.DEFAULT_PRODUCT,))
