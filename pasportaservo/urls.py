from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth.views import (login, logout,
    password_change, password_change_done,
    password_reset, password_reset_done, password_reset_confirm, password_reset_complete)
from django.utils.translation import ugettext_lazy as _


urlpatterns = patterns('',
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(_(r'^login/$'),
        view='django.contrib.auth.views.login',
        name='login'),
    url(_(r'^logout/$'),
        view='django.contrib.auth.views.logout',
        kwargs={'next_page':'/'},
        name='logout'),
    url(_(r'^password/$'),
        view='django.contrib.auth.views.password_change',
        name='password_change'),
    url(_(r'^password/done/$'),
        view='django.contrib.auth.views.password_change_done',
        name='password_change_done'),
    url(_(r'^password/reset/$'),
        view='django.contrib.auth.views.password_reset',
        name='password_reset'),
    url(_(r'^password/reset/done/$'),
        view='django.contrib.auth.views.password_reset_done',
        name='password_reset_done'),
    url(_(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'),
        view='django.contrib.auth.views.password_reset_confirm',
        name='password_reset_confirm'),
    url(_(r'^reset/done/$'),
        view='django.contrib.auth.views.password_reset_complete',
        name='password_reset_complete'),

    url('', include('hosting.urls')),
    url('', include('pages.urls')),
)
