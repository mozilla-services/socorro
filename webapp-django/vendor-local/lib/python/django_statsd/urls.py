from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url('^record$', 'django_statsd.views.record',
        name='django_statsd.record'),
)
