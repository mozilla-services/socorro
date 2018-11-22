from django.conf.urls import url

from crashstats.topcrashers import views


app_name = 'topcrashers'
urlpatterns = [
    url(r'^$',
        views.topcrashers,
        name='topcrashers'),
]
