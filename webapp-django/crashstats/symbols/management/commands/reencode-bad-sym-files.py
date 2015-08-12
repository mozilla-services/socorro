import gzip
from cStringIO import StringIO

from optparse import make_option

import requests
import boto.s3.connection

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.defaultfilters import filesizeformat
from django.utils import timezone

from crashstats.symbols.models import SymbolsUpload


class Command(BaseCommand):
    """
    On July 20 2015 we released an improvement to the symbols uploader so
    that all .sym files in the zip archive bundles would be gzipped.
    That makes them smaller.
    However, we made a mistake in that we didn't encode the file correctly,
    just encoding the content.
    To correct this we have this script.
    """

    help = (
        'Run this command to re-encode .sym files that were uploaded '
        'without first being properly encoded with the gzip header signature.'
    )

    option_list = BaseCommand.option_list + (
        make_option(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Only find the files to re-encode'
        ),
        make_option(
            '--first-date',
            dest='first_date',
            default='2015-07-20',  # the day we started compressing (132)
            help='Upload date range start'
        ),
        make_option(
            '--end-date',
            dest='end_date',
            default='2015-08-05',  # the day the fix was release on prod (134)
            help='Upload date range end'
        ),
        make_option(
            '--max-uploads',
            dest='max_uploads',
            default='0',
            help='Max. number of SymbolsUploads to work on (default all)'
        ),
    )

    def _parse_date(self, date):
        year, month, day = [int(x) for x in date.split('-')]
        return timezone.now().replace(
            year=year,
            month=month,
            day=day,
            hour=0,
            minute=0,
            second=0
        )

    def handle(self, *args, **options):
        first_date = self._parse_date(options['first_date'])
        end_date = self._parse_date(options['end_date'])
        max_uploads = int(options['max_uploads'])
        uploads = SymbolsUpload.objects.filter(
            created__gte=first_date,
            created__lt=end_date
        )
        buckets = {}
        conn = boto.connect_s3(
            settings.AWS_ACCESS_KEY,
            settings.AWS_SECRET_ACCESS_KEY,
            calling_format=boto.s3.connection.OrdinaryCallingFormat()
        )
        if max_uploads > 0:
            uploads = uploads.order_by('?')[:max_uploads]
        for upload in uploads:
            print repr(upload)
            for line in upload.content.splitlines():
                if not line.endswith('.sym'):
                    continue
                bucket_name = line.split(',')[0]
                if bucket_name.startswith('+') or bucket_name.startswith('='):
                    bucket_name = bucket_name[1:]
                if bucket_name not in buckets:
                    buckets[bucket_name] = conn.lookup(bucket_name)

                if not buckets[bucket_name]:
                    print "No bucket called", repr(bucket_name)
                    continue

                key = buckets[bucket_name].get_key(line.split(',')[1])
                if key is not None:
                    assert key.content_type == 'text/plain', key.content_type
                    assert key.content_encoding == 'gzip', key.content_encoding
                    print filesizeformat(key.size).ljust(10),
                    url = key.generate_url(expires_in=0, query_auth=False)
                    print url
                    if self._correctly_encoded(url):
                        print "CORRECTLY ENCODED"
                    else:
                        print "NOT CORRECT",
                        if not options['dry_run']:
                            downloaded = key.get_contents_as_string()
                            real_content = downloaded.decode('zlib')
                            out = StringIO()
                            with gzip.GzipFile(fileobj=out, mode='w') as f:
                                f.write(real_content)
                            value = out.getvalue()
                            key.set_contents_from_string(value, {
                                'Content-Encoding': 'gzip'
                            })
                            print "FIXED"
                        else:
                            print "DRY-RUN"

    def _correctly_encoded(self, url):
        try:
            requests.get(url)
            return True
        except requests.exceptions.ContentDecodingError:
            return False
