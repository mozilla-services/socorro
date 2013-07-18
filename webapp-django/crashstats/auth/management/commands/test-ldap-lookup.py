from django.core.management.base import BaseCommand
from crashstats.auth.views import in_allowed_group


class Command(BaseCommand):  # pragma: no cover

    args = 'emailaddress'

    def handle(self, mail, **options):
        if in_allowed_group(mail):
            print "YES!"
        else:
            print "No go :("
