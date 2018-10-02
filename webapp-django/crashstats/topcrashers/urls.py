from django.conf.urls import url
from . import views


app_name = 'topcrashers'
urlpatterns = [
    url(r'^$',
        views.topcrashers,
        name='topcrashers'),
]
