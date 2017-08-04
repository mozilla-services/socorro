from __future__ import print_function

try:
    _input = raw_input
except NameError:
    # You're on Python >=3
    _input = input

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from crashstats.authentication.views import default_username


def get_input(text):
    return _input(text).strip()


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('emailaddress', nargs='+', type=str)

    def handle(self, **options):
        emails = options['emailaddress']
        if not emails:
            emails = [get_input('Email address: ').strip()]
        if not [x for x in emails if x.strip()]:
            raise CommandError('Must supply at least one email address')
        for email in emails:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user = User.objects.create(
                    username=default_username(email),
                    email=email,
                )
                user.set_unusable_password()

            if user.is_superuser:
                print('{} was already a superuser'.format(user.email))
            else:
                user.is_superuser = True
                user.save()
                print('{} is now a superuser'.format(user.email))
