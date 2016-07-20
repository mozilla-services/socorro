import csv

from django.core.management.base import BaseCommand

from crashstats.authentication.migration import migrate_users


class Command(BaseCommand):
    help = """Parsing a CSV file where the first column is the
    ALIAS email and the second column is the CORRECT email.
    """

    def add_arguments(self, parser):
        parser.add_argument('csvfile')

        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Print instead of actually merging'
        )

        parser.add_argument(
            '--include-first-row',
            action='store_true',
            default=False,
            help='Set if the first row is NOT a header'
        )

    def handle(self, **options):
        first = True
        combos = []
        with open(options['csvfile']) as f:
            reader = csv.reader(f)
            for row in reader:
                if first and not options['include_first_row']:
                    first = False
                else:
                    assert len(row) == 2, len(row)
                    combos.append(row)

        migrate_users(combos, dry_run=options['dry_run'])
