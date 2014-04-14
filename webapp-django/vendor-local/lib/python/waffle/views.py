from django.core.cache import cache
from django.shortcuts import render_to_response
from django.views.decorators.cache import never_cache

from waffle import (flag_is_active, sample_is_active, FLAGS_ALL_CACHE_KEY,
                    SWITCHES_ALL_CACHE_KEY, SAMPLES_ALL_CACHE_KEY)
from waffle.models import Flag, Sample, Switch
from django.conf import settings


@never_cache
def wafflejs(request):
    flags = cache.get(FLAGS_ALL_CACHE_KEY)
    if not flags:
        flags = Flag.objects.values_list('name', flat=True)
        cache.add(FLAGS_ALL_CACHE_KEY, flags)
    flag_values = [(f, flag_is_active(request, f)) for f in flags]

    switches = cache.get(SWITCHES_ALL_CACHE_KEY)
    if not switches:
        switches = Switch.objects.values_list('name', 'active')
        cache.add(SWITCHES_ALL_CACHE_KEY, switches)

    samples = cache.get(SAMPLES_ALL_CACHE_KEY)
    if not samples:
        samples = Sample.objects.values_list('name', flat=True)
        cache.add(SAMPLES_ALL_CACHE_KEY, samples)
    sample_values = [(s, sample_is_active(s)) for s in samples]

    flag_default = getattr(settings, 'WAFFLE_FLAG_DEFAULT', False)
    switch_default = getattr(settings, 'WAFFLE_SWITCH_DEFAULT', False)
    sample_default = getattr(settings, 'WAFFLE_SAMPLE_DEFAULT', False)

    return render_to_response('waffle/waffle.js',
                              {
                                'flags': flag_values,
                                'switches': switches,
                                'samples': sample_values,
                                'flag_default': flag_default,
                                'switch_default': switch_default,
                                'sample_default': sample_default,
                              },
                              mimetype='application/x-javascript')
