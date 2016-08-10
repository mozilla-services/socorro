from crashstats.status.models import StatusMessage


def status_message(request):
    statuses = StatusMessage.objects.filter(enabled=True)

    if not statuses.exists():
        return {}

    messages = []
    for status in statuses.order_by('-created_at'):
        messages.append({
            'text': status.message,
            'severity': status.severity,
            'date': status.created_at,
        })

    return {
        'status_messages': messages,
    }
