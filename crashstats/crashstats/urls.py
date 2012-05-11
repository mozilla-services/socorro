from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to
from . import views


urlpatterns = patterns('',
    url(r'^products/(?P<product>\w+)$', views.home,
        name='crashstats.products'),
    url(r'^products/(?P<product>\w+)/versions/(?P<versions>\w+\.\w+)$',
        views.home,
        name='crashstats.products'),
    url(r'^topcrasher/byversion/(?P<product>\w+)/(?P<version>\w+\.\w+)$',
        views.topcrasher,
        name='crashstats.topcrasher'),
    url(r'^daily$', views.daily,
        name='crashstats.daily'),
    url(r'^products/(?P<product>\w+)/builds$', views.builds,
        name='crashstats.builds'),
    url(r'^hangreport/byversion/(?P<product>\w+)/$', views.hangreport,
        name='crashstats.hangreport'),
    url(r'^products/(?P<product>\w+)/topchangers$', views.topchangers,
        name='crashstats.topchangers'),
    url(r'^report/list$', views.reportlist,
        name='crashstats.reportlist'),
    url(r'^report/index/\w+$', views.reportindex,
        name='crashstats.reportindex'),
    url(r'^query$', views.query,
        name='crashstats.query'),
    url(r'^$', redirect_to, {'url': '/products/Firefox'}),
)
