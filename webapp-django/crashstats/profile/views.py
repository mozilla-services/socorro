import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import Permission

from crashstats.crashstats.decorators import pass_default_context
from crashstats.supersearch.models import SuperSearchUnredacted


@pass_default_context
@login_required
def profile(request, default_context=None):
    context = default_context or {}
    context['permissions'] = (
        Permission.objects.filter(content_type__model='')
        .order_by('name')
    )

    start_date = (
        datetime.datetime.utcnow() - datetime.timedelta(weeks=4)
    ).isoformat()

    api = SuperSearchUnredacted()
    results = api.get(
        email=request.user.email,
        date='>%s' % start_date,
        _columns=['date', 'uuid'],
        _sort='-date',
    )

    context['crashes_list'] = [
        dict(zip(('crash_id', 'date'), (x['uuid'], x['date'])))
        for x in results['hits']
    ]

    return render(request, 'profile/profile.html', context)
