from crashstats.status.models import StatusMessage


def status_message(request):
    statuses = (
        StatusMessage.objects.filter(enabled=True).order_by('-created_at')
    )

    if not statuses.count():
        return {}

    messages = []
    for status in statuses:
        messages.append({
            'text': status.message,
            'severity': status.severity,
        })

    return {
        'status_messages': messages,
    }
