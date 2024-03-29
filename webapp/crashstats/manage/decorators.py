# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth.decorators import REDIRECT_FIELD_NAME, user_passes_test


def superuser_required(
    function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None
):
    """Same logic as in login_required() (see doc string above) but with
    the additional check that we require you to be superuser also.
    """

    def check_user(user):
        return user.is_active and user.is_superuser

    actual_decorator = user_passes_test(
        check_user, login_url=login_url, redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
