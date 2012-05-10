from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to
from . import views


urlpatterns = patterns('',
    url(r'^products/\w+$', views.home,
        name='crashstats.products'),
    url(r'^topcrasher/byversion/.*$', views.topcrasher,
        name='crashstats.topcrasher'),
    url(r'^daily$', views.daily,
        name='crashstats.daily'),
    url(r'^daily$', views.daily,
        name='crashstats.daily'),
    url(r'^products/daily/builds$', views.builds,
        name='crashstats.builds'),
    url(r'^hangreport/byversion/\w+/\w+$', views.hangreport,
        name='crashstats.hangreport'),
    url(r'^products/\w+/versions/\w+/topchangers$', views.topchangers,
        name='crashstats.topchangers'),
    url(r'^report/list$', views.reportlist,
        name='crashstats.reportlist'),
    url(r'^report/index/\w+$', views.reportindex,
        name='crashstats.reportindex'),
    url(r'^query$', views.query,
        name='crashstats.query'),
    url(r'^$', redirect_to, {'url': '/products/Firefox'}),
)
