from crashstats.status.models import StatusMessage


def status_message(request):
    return {
        'status_messages': (
            StatusMessage.objects.filter(enabled=True).order_by('-created_at')
        ),
    }
