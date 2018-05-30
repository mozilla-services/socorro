from django.conf.urls import url

from . import views


app_name = 'manage'
urlpatterns = [
    url('^$',
        views.home,
        name='home'),
    url('^analyze-model-fetches/$',
        views.analyze_model_fetches,
        name='analyze_model_fetches'),
    url('^graphics-devices/$',
        views.graphics_devices,
        name='graphics_devices'),
    url('^graphics-devices/lookup/$',
        views.graphics_devices_lookup,
        name='graphics_devices_lookup'),
    url('^supersearch-fields/missing/$',
        views.supersearch_fields_missing,
        name='supersearch_fields_missing'),
    url('^events/$',
        views.events,
        name='events'),
    url('^events/data/$',
        views.events_data,
        name='events_data'),
    url('^status/$',
        views.status_message,
        name='status_message'),
    url('^status/disable/(?P<id>\d+)/$',
        views.status_message_disable,
        name='status_message_disable'),
    url('^crash-me-now/$',
        views.crash_me_now,
        name='crash_me_now'),
    url('^reprocessing/$',
        views.reprocessing,
        name='reprocessing'),
    url('^sitestatus/$',
        views.site_status,
        name='site_status'),
]
