# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from crashstats.tokens.models import Token


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = [
        "key_truncated",
        "get_user_email",
        "get_permissions",
        "expires",
        "notes",
    ]

    list_filter = ["permissions"]
    search_fields = ["user__email", "notes"]

    def key_truncated(self, obj):
        return obj.key[:12] + "..."

    def get_permissions(self, obj):
        return ", ".join(perm.codename for perm in obj.permissions.all())

    def get_user_email(self, obj):
        return obj.user.email
