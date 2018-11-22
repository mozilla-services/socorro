from django.conf.urls import url

from crashstats.sources import views


app_name = 'sources'
urlpatterns = [
    url(r'^highlight/$',
        views.highlight_url,
        name='highlight_url'),
]
