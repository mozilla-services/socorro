from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION


# Fix the Django Admin User list display so it shows the columns we care about
UserAdmin.list_display = [
    'email',
    'first_name',
    'last_name',
    'is_superuser',
    'is_staff',
    'is_active',
    'date_joined',
    'last_login'
]


ACTION_TO_NAME = {
    ADDITION: 'add',
    CHANGE: 'change',
    DELETION: 'delete'
}


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'action_time'

    list_display = [
        'action_time',
        'user_email',
        'content_type',
        'object_repr',
        'action_name',
        'get_change_message'
    ]

    def user_email(self, obj):
        return obj.user.email

    def action_name(self, obj):
        return ACTION_TO_NAME[obj.action_flag]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # NOTE(willkg): If this always returned False, then this modeladmin
        # doesn't show up in the index. However, this means you get a change
        # page that suggests you can change it, but errors out when saving.
        return request.method != 'POST'

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return True
