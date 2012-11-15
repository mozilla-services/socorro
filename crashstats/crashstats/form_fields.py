import datetime

from django.conf import settings
from django import forms


class CarefulFieldBase(object):
    """Because Django's forms.fields.DateTimeField class is not careful
    enough when it uses datetime.datetime.strptime() to try to convert
    we improve that by using our own.

    We need this till
    https://github.com/django/django/commit/\
      3174b5f2f5bb0b0a6b775a1a50464b6bf2a4b067
    is included in the next release.
    """

    def strptime(self, value, format):
        try:
            return datetime.datetime.strptime(value, format)
        except TypeError, e:
            raise ValueError(e)


class CarefulDateTimeField(CarefulFieldBase, forms.DateTimeField):
    pass


class CarefulDateField(CarefulFieldBase, forms.DateField):
    pass


class SignatureField(forms.CharField):
    # to use whenever you need a `signature` field

    def __init__(self, *args, **kwargs):
        if not kwargs.get('max_length'):
            kwargs['max_length'] = settings.SIGNATURE_MAX_LENGTH
        super(SignatureField, self).__init__(*args, **kwargs)
