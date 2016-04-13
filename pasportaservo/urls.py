from __future__ import unicode_literals

from django.conf.urls import include, url
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _


urlpatterns = [
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
]

urlpatterns += [
    url(r'^grappelli/', include('grappelli.urls')),
    url(_(r'^admin/'), include(admin.site.urls)),
    url(_(r'^messages/'), include('postman.urls', namespace='postman', app_name='postman')),
    url('', include('hosting.urls')),
    url('', include('pages.urls')),
]
