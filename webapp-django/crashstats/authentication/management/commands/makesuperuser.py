import sys

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


def get_input(text):
    return raw_input(text).strip()


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
                print >> sys.stderr, "No user with that email %s" % (email,)
                break
            if user.is_superuser:
                print >> sys.stdout, (
                    '%s was already a superuser' % (user.email,)
                )
            else:
                user.is_superuser = True
                user.save()
                print >> sys.stdout, (
                    '%s is now a superuser' % (user.email,)
                )
