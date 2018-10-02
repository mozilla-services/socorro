from django.conf.urls import url
from . import views


app_name = 'sources'
urlpatterns = [
    url(r'^highlight/$',
        views.highlight_url,
        name='highlight_url'),
]
