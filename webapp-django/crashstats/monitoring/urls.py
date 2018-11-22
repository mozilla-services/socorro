from django.conf.urls import url

from crashstats.monitoring import views


app_name = 'monitoring'
urlpatterns = [
    url(r'^$',
        views.index,
        name='index'),
    url(r'^crontabber/$',
        views.crontabber_status,
        name='crontabber_status'),
    url(r'^healthcheck/$',
        views.healthcheck,
        name='healthcheck'),
]
