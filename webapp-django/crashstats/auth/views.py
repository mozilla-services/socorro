import re

import ldap
from ldap.filter import filter_format

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.core.exceptions import ImproperlyConfigured

from django_browserid.views import Verify


def in_allowed_group(mail):
    """Return True if the email address is in one of the
    settings.LDAP_GROUP_NAMES groups.
    """

    def make_search_filter(data, any_parameter=False):
        params = []
        for key, value in data.items():
            if not isinstance(value, (list, tuple)):
                value = [value]
            for v in value:
                if not v:
                    v = 'TRUE'
                params.append(filter_format('(%s=%s)', (key, v)))
        search_filter = ''.join(params)
        if len(params) > 1:
            if any_parameter:
                search_filter = '(|%s)' % search_filter
            else:
                search_filter = '(&%s)' % search_filter
        return search_filter

    conn = ldap.initialize(settings.LDAP_SERVER_URI)
    conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
    for opt, value in getattr(settings, 'LDAP_GLOBAL_OPTIONS', {}).items():
        conn.set_option(opt, value)
    conn.simple_bind_s(
        settings.LDAP_BIND_DN,
        settings.LDAP_BIND_PASSWORD
    )

    mail_filter = make_search_filter(dict(mail=mail))
    alias_filter = make_search_filter(dict(emailAlias=mail))
    search_filter = '(|%s%s)' % (mail_filter, alias_filter)

    rs = conn.search_s(
        settings.LDAP_SEARCH_BASE_USER,
        ldap.SCOPE_SUBTREE,
        search_filter,
        ['uid']
    )
    # `rs` is an iterator, so we can't simply do `rs[0]` on it
    for uid, result in rs:
        break
    else:
        # exit early
        return False

    # because the original mail could have been an alias,
    # switch to the real one
    try:
        mail = re.findall('mail=(.*?),', uid)[0]
    except IndexError:
        # can't use alias, but that's ok
        pass

    search_filter1 = make_search_filter(dict(cn=settings.LDAP_GROUP_NAMES))
    _template_data = {'mail': mail, 'uid': uid}
    search_filter2 = make_search_filter({
        'memberUID': [uid, mail],
        'member': [x % _template_data for x in
                   settings.LDAP_GROUP_QUERIES],
    }, any_parameter=True)
    search_filter = '(&%s%s)' % (search_filter1, search_filter2)

    rs = conn.search_s(
        settings.LDAP_SEARCH_BASE_GROUP,
        ldap.SCOPE_SUBTREE,
        search_filter,
        ['cn']
    )

    for __ in rs:
        return True

    return False


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

    def login_success(self):
        """the user passed the BrowserID hurdle, but are they vouced for
        in LDAP?"""
        for name in ('LDAP_BIND_DN', 'LDAP_BIND_PASSWORD', 'LDAP_GROUP_NAMES'):
            if not getattr(settings, name, None):  # pragma: no cover
                raise ImproperlyConfigured(
                    "Not configured `settings.%s`" % name
                )
        debug_email_addresses = getattr(
            settings,
            'DEBUG_LDAP_EMAIL_ADDRESSES',
            []
        )
        if debug_email_addresses and not settings.DEBUG:
            raise SuspiciousOperation(
                "Can't debug login when NOT in DEBUG mode"
            )  # NOQA
        if (
            self.user.email in debug_email_addresses or
            in_allowed_group(self.user.email)
        ):
            messages.success(
                self.request,
                'You have successfully logged in.'
            )
            return super(CustomBrowserIDVerify, self).login_success()
        else:
            messages.error(
                self.request,
                "You logged in as {email} but you don't have sufficient "
                "privileges.".format(email=self.user.email)
            )
            return super(CustomBrowserIDVerify, self).login_failure()
