import re
import logging

import ldap
from ldap.filter import filter_format

from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation

from django_browserid.base import get_audience
from django_browserid.auth import verify
from django_browserid.forms import BrowserIDForm


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


@require_POST
def mozilla_browserid_verify(request):
    """Custom BrowserID verifier for mozilla addresses."""
    home_url = reverse('crashstats.home',
                       args=(settings.DEFAULT_PRODUCT,))
    goto_url = request.POST.get('goto', None) or home_url
    form = BrowserIDForm(request.POST)
    if form.is_valid():
        assertion = form.cleaned_data['assertion']
        audience = get_audience(request)
        result = verify(assertion, audience)

        for name in ('LDAP_BIND_DN', 'LDAP_BIND_PASSWORD', 'LDAP_GROUP_NAMES'):
            if not getattr(settings, name, None):  # pragma: no cover
                raise ValueError(
                    "Not configured `settings.%s`" % name
                )

        if result:
            allowed = in_allowed_group(result['email'])
            debug_email_addresses = getattr(
                settings,
                'DEBUG_LDAP_EMAIL_ADDRESSES',
                []
            )
            if debug_email_addresses and not settings.DEBUG:
                raise SuspiciousOperation(
                    "Can't debug login when NOT in DEBUG mode"
                )
            if allowed or result['email'] in debug_email_addresses:
                if allowed:
                    logging.info('%r is in an allowed group', result['email'])
                else:
                    logging.info('%r allowed for debugging', result['email'])
                user = auth.authenticate(assertion=assertion,
                                         audience=audience)
                auth.login(request, user)
                messages.success(
                    request,
                    'You have successfully logged in.'
                )
            else:
                if not allowed:
                    logging.info('%r NOT in an allowed group', result['email'])
                messages.error(
                    request,
                    "You logged in as %s but you don't have sufficient "
                    "privileges." % result['email']
                )
    else:
        messages.error(
            request,
            "Login failed"
        )
    return redirect(goto_url)
