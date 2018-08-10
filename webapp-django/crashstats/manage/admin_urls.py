from django.conf.urls import url

from . import admin


urlpatterns = [
    url('^analyze-model-fetches/$',
        admin.analyze_model_fetches,
        name='analyze_model_fetches'),
    url('^crash-me-now/$',
        admin.crash_me_now,
        name='crash_me_now'),
    url('^debug-view/$',
        admin.debug_view,
        name='debug_view'),
    url('^graphics-devices/$',
        admin.graphics_devices,
        name='graphics_devices'),
    url('^graphics-devices/lookup/$',
        admin.graphics_devices_lookup,
        name='graphics_devices_lookup'),
    url('^products/$',
        admin.products,
        name='products'),
    url('^sitestatus/$',
        admin.site_status,
        name='site_status'),
    url('^supersearch-fields/missing/$',
        admin.supersearch_fields_missing,
        name='supersearch_fields_missing'),
]
