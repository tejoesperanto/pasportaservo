from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.utils.translation import ugettext_lazy as _


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'pasportaservo.views.home', name='home'),
    # url(r'^pasportaservo/', include('pasportaservo.foo.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(_(r'^login/'), login, name='login'),
    url(_(r'^logout/'), logout, name='logout'),
    url(r'', include('hosting.urls')),
)
