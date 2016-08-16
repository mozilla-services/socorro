import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from crashstats.crashstats import models as crashstats_models


class SymbolsUpload(models.Model):
    user = models.ForeignKey(User)
    content = models.TextField()
    filename = models.CharField(max_length=100)
    size = models.IntegerField()
    created = models.DateTimeField(default=timezone.now)
    content_type = models.TextField(null=True)

    def __repr__(self):
        return '<%s: id=%s filename="%s" size=%d>' % (
            self.__class__.__name__,
            self.id,
            self.filename,
            self.size
        )


class UploadedSymbols(crashstats_models.SocorroMiddleware):
    """
    An API to find past uploads and see what S3 keys where in the
    archive. And out of the S3 keys, you will be able to see which
    ones were new or different and which were uploaded under the
    existing key.
    """
    # Don't have to worry about stampeding herds on this
    # model because it requires a permission anyway.
    cache_seconds = 0

    required_params = (
        ('start_date', datetime.date),
        ('end_date', datetime.date),
    )
    possible_params = (
        'user_search',
        'filename_search',
        'content_search',
    )

    API_WHITELIST = {
        'hits': (
            'id',
            'user',
            'filename',
            'content',
            'date',
            'size',
            'content_type'
        ),

    }

    API_REQUIRED_PERMISSIONS = (
        'crashstats.view_all_symbol_uploads',
    )

    def get(self, **kwargs):
        # Note! This API is not cached.

        # We're going to compare a datetime.date with a timezone aware
        # datetime.datetime object, so we need to convert the datetime.date.
        start_date = datetime.datetime.combine(
            kwargs['start_date'],
            datetime.datetime.min.time()
        )
        end_date = datetime.datetime.combine(
            kwargs['end_date'],
            datetime.datetime.min.time()
        )
        start_date = start_date.replace(tzinfo=timezone.utc)
        end_date = end_date.replace(tzinfo=timezone.utc)
        query = SymbolsUpload.objects.filter(
            created__gte=start_date,
            created__lt=end_date + datetime.timedelta(days=1),
        ).order_by('-created')
        if kwargs.get('user_search'):
            query = query.filter(user__email__icontains=kwargs['user_search'])
        if kwargs.get('filename_search'):
            query = query.filter(filename__icontains=kwargs['filename_search'])
        if kwargs.get('content_search'):
            query = query.filter(content__icontains=kwargs['content_search'])

        query = query.select_related('user')
        hits = []

        for upload in query:
            added = []
            existed = []
            for line in upload.content.splitlines():
                path = line[1:]
                if line[0] == '+':
                    added.append(path)
                else:
                    existed.append(path)
            hits.append({
                'id': upload.id,
                'user': upload.user.email,
                'filename': upload.filename,
                'content': {
                    'added': added,
                    'existed': existed,
                },
                'date': upload.created,
                'size': upload.size,
                'content_type': upload.content_type,
            })
        return {
            'hits': hits,
            'total': query.count(),
        }
