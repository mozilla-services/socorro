from crashstats.status.models import StatusMessage


def status_message(request):
    statuses = (
        StatusMessage.objects.filter(enabled=True).order_by('-created_at')
    )

    if not len(statuses):
        return {}

    status = statuses[0]
    return {
        'status_message': {
            'text': status.message,
            'severity': status.severity,
        },
    }
