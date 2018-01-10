import datetime

from django.conf import settings
from django.utils import timezone


def oauth2(request):
    # By default we don't want to encourage the client-side code to
    # sign out, so set this to a falsy value.
    signout = False
    if getattr(request, 'user', None) and request.user.is_authenticated:
        # NOTE On the future; If we *had* a way to check if a member of
        # staff has ceased to be member of staff, here would be a
        # good place to ask that question. Then we could stop bothering
        # with dates/seconds and entirely go by the fact that the user
        # has supposedly left LDAP as a member of staff.

        if not request.user.is_active:
            signout = True
        else:
            diff = timezone.now() - request.user.last_login
            max_diff = datetime.timedelta(seconds=settings.LAST_LOGIN_MAX)
            if diff >= max_diff:
                # The server is instructing the DOM so that the loaded
                # JavaScript takes heed and signs the user out.
                signout = True

    return {
        'OAUTH2_CLIENT_ID': settings.OAUTH2_CLIENT_ID,
        'OAUTH2_SIGNOUT': signout,
    }
