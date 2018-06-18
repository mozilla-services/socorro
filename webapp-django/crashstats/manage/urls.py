from django.conf.urls import url

from . import views


app_name = 'manage'
urlpatterns = [
    url('^$',
        views.home,
        name='home'),
    url('^graphics-devices/$',
        views.graphics_devices,
        name='graphics_devices'),
    url('^graphics-devices/lookup/$',
        views.graphics_devices_lookup,
        name='graphics_devices_lookup'),
    url('^supersearch-fields/missing/$',
        views.supersearch_fields_missing,
        name='supersearch_fields_missing'),
]
