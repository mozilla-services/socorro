from django.conf.urls import url

from . import admin


urlpatterns = [
    url('^crash-me-now/$',
        admin.crash_me_now,
        name='crash_me_now'),
]
