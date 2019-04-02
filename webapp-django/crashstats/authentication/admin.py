# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from crashstats.authentication.models import PolicyException


@admin.register(PolicyException)
class PolicyExceptionAdmin(admin.ModelAdmin):
    """Admin page for PolicyExceptions."""

    list_display = [
        'get_user_email',
        'comment',
        'created',
        'user_linked',
    ]

    search_fields = ['user__email', 'notes']

    def get_user_email(self, obj):
        return obj.user.email

    def user_linked(self, obj):
        url = reverse('admin:auth_user_change', args=(obj.user.id,))
        return format_html('<a href="{}">{}</a>', url, url)
