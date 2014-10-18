from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth.views import (login, logout,
    password_change, password_change_done,
    password_reset, password_reset_done, password_reset_confirm)
from django.utils.translation import ugettext_lazy as _


urlpatterns = patterns('',
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(_(r'^login/$'), login, name='login'),
    url(_(r'^logout/$'), logout, {'next_page':'/'}, name='logout'),
    url(_(r'^password/$'), password_change, name='password_change'),
    url(_(r'^password/done/$'), password_change_done  , name='password_change_done'),
    url(_(r'^password/reset/$'), password_reset, name='password_reset'),
    url(_(r'^password/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'), 
        'password_reset_confirm', name='password_reset_confirm'),
    url(_(r'^password/reset/done/$'), password_reset_done, name='password_reset_done'),
    # url(_(r'^password/reset/confirm/$'), password_reset_confirm, name='password_reset_confirm'),

    url(r'', include('hosting.urls')),
    url(_(r'^pages/'), include('pages.urls')),
)

