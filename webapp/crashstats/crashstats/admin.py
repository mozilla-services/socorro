# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.auth.models import User
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html

from crashstats.crashstats.models import (
    BugAssociation,
    GraphicsDevice,
    MissingProcessedCrash,
    Platform,
    ProductVersion,
    Signature,
    # Middleware
    PriorityJob,
)


ACTION_TO_NAME = {ADDITION: "add", CHANGE: "change", DELETION: "delete"}


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = "action_time"

    list_display = [
        "action_time",
        "admin_email",
        "object_link",
        "action",
        "get_change_message",
    ]
    list_display_links = ["action_time", "get_change_message"]

    def admin_email(self, obj):
        return obj.user.email

    def action(self, obj):
        return ACTION_TO_NAME[obj.action_flag]

    def obj_repr(self, obj):
        edited_obj = obj.get_edited_object()

        if isinstance(edited_obj, User):
            # For user objects, return the email address as an identifier
            return edited_obj.email
        return edited_obj

    @admin.display(
        description="object",
        ordering="object_repr",
    )
    def object_link(self, obj):
        object_link = self.obj_repr(obj)  # Default to just name
        content_type = obj.content_type

        if obj.action_flag != DELETION and content_type is not None:
            # try returning an actual link instead of object repr string
            try:
                url = reverse(
                    "admin:{}_{}_change".format(
                        content_type.app_label, content_type.model
                    ),
                    args=[obj.object_id],
                )
                object_link = format_html('<a href="{}">{}</a>', url, object_link)
            except NoReverseMatch:
                pass
        return object_link

    @admin.display(description="change message")
    def get_change_message(self, obj):
        return obj.get_change_message()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BugAssociation)
class BugAssociationAdmin(admin.ModelAdmin):
    list_display = ["bug_id", "signature"]
    search_fields = ["bug_id", "signature"]


@admin.register(GraphicsDevice)
class GraphicsDeviceAdmin(admin.ModelAdmin):
    list_display = ["id", "vendor_hex", "adapter_hex", "vendor_name", "adapter_name"]
    search_fields = ["vendor_hex", "adapter_hex", "vendor_name", "adapter_name"]


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name"]


@admin.register(ProductVersion)
class ProductVersionAdmin(admin.ModelAdmin):
    list_display = [
        "product_name",
        "release_channel",
        "major_version",
        "release_version",
        "version_string",
        "build_id",
        "archive_url",
    ]

    search_fields = ["version_string"]

    list_filter = ["major_version", "product_name", "release_channel"]


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ["signature", "first_build", "first_date"]
    search_fields = ["signature"]


@admin.action(description="Process crashes")
def process_crashes(modeladmin, request, queryset):
    """Process selected missing processed crashes from admin page."""
    priority_api = PriorityJob()
    crash_ids = list(queryset.values_list("crash_id", flat=True))
    priority_api.post(crash_ids=crash_ids)
    messages.add_message(
        request, messages.INFO, "Sent %s crashes for processing." % len(crash_ids)
    )


@admin.register(MissingProcessedCrash)
class MissingProcessedCrashAdmin(admin.ModelAdmin):
    list_display = [
        "crash_id",
        "created",
        "collected_date",
        "is_processed",
        "report_url_linked",
    ]
    actions = [process_crashes]

    list_filter = ["is_processed"]

    def report_url_linked(self, obj):
        return format_html('<a href="{}">{}</a>', obj.report_url(), obj.report_url())
