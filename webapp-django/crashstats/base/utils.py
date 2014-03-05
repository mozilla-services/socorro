import datetime

from django.utils.timezone import utc


def get_now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)
