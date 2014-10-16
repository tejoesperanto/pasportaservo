from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.utils.translation import ugettext_lazy as _


urlpatterns = patterns('',
    url(r'^grappelli/', include('grappelli.urls')), # grappelli URLS
    url(r'^admin/', include(admin.site.urls)),
    url(_(r'^login/$'), login, name='login'),
    url(_(r'^logout/$'), logout, {'next_page':'/'}, name='logout'),
    url(r'', include('hosting.urls')),
    url(_(r'^pages/'), include('pages.urls')),
)

