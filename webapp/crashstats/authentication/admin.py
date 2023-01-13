# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html

from crashstats.authentication.models import PolicyException


# Unregister the original UserAdmin and register our better one
try:
    admin.site.unregister(User)
except TypeError:
    pass


@admin.register(User)
class UserAdminBetter(UserAdmin):
    """Improved UserAdmin.

    This shows columns we care about and has links to PolicyException manipulation.

    """

    list_display = [
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_hacker",
        "is_superuser",
        "date_joined",
        "last_login",
        "get_policyexception",
    ]

    def is_hacker(self, obj):
        """Return whether user is in the Hackers group and has access to PII."""
        return obj.groups.filter(name="Hackers").exists()

    is_hacker.short_description = "Hacker (PII)"

    def get_policyexception(self, obj):
        """Return whether user has a PolicyException with links to change/delete or add one."""
        if hasattr(obj, "policyexception"):
            url = reverse(
                "admin:authentication_policyexception_change",
                args=(obj.policyexception.id,),
            )
            return format_html('YES | <a href="{}">Change/Delete</a>', url)
        url = reverse("admin:authentication_policyexception_add") + (
            "?user=%d" % obj.id
        )
        return format_html('<a href="{}">Create</a>', url)

    get_policyexception.short_description = "PolicyException"


@admin.register(PolicyException)
class PolicyExceptionAdmin(admin.ModelAdmin):
    """Admin page for PolicyExceptions."""

    list_display = ["get_user_email", "comment", "created", "user_linked"]
    search_fields = ["user__email", "notes"]

    def get_user_email(self, obj):
        return obj.user.email

    def user_linked(self, obj):
        url = reverse("admin:auth_user_change", args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, url)
