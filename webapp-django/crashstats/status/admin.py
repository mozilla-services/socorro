from django.contrib import admin

from crashstats.status.models import StatusMessage


@admin.register(StatusMessage)
class StatusMessageAdmin(admin.ModelAdmin):
    list_display = [
        'message',
        'severity',
        'enabled',
        'created_at',
    ]
