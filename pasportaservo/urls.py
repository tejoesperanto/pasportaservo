from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'pasportaservo.views.home', name='home'),
    # url(r'^pasportaservo/', include('pasportaservo.foo.urls')),

    url(r'^admin/', include(admin.site.urls)),
)
