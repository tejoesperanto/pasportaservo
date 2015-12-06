from __future__ import unicode_literals

from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView
from django.core.urlresolvers import reverse_lazy
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from postman import OPTIONS
from postman import views as postman_views

urlpatterns = patterns('',
    url(r'^grappelli/', include('grappelli.urls')),
    url(_(r'^admin/'), include(admin.site.urls)),

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


    url(_(r'^messages/inbox/(?:(?P<option>m)/)?$'), postman_views.InboxView.as_view(), name='postman_inbox'),
    url(_(r'^messages/sent/(?:(?P<option>m)/)?$'), postman_views.SentView.as_view(), name='postman_sent'),
    url(_(r'^messages/archives/(?:(?P<option>m)/)?$'), postman_views.ArchivesView.as_view(), name='postman_archives'),
    url(_(r'^messages/trash/(?:(?P<option>m)/)?$'), postman_views.TrashView.as_view(), name='postman_trash'),
    url(_(r'^messages/write/(?:(?P<recipients>[^/#]+)/)?$'), postman_views.WriteView.as_view(), name='postman_write'),
    url(_(r'^messages/reply/(?P<message_id>[\d]+)/$'), postman_views.ReplyView.as_view(), name='postman_reply'),
    url(_(r'^messages/view/(?P<message_id>[\d]+)/$'), postman_views.MessageView.as_view(), name='postman_view'),
    url(_(r'^messages/view/t/(?P<thread_id>[\d]+)/$'), postman_views.ConversationView.as_view(), name='postman_view_conversation'),
    url(_(r'^messages/archive/$'), postman_views.ArchiveView.as_view(), name='postman_archive'),
    url(_(r'^messages/delete/$'), postman_views.DeleteView.as_view(), name='postman_delete'),
    url(_(r'^messages/undelete/$'), postman_views.UndeleteView.as_view(), name='postman_undelete'),
    url(_(r'^messages/$'), RedirectView.as_view(url=reverse_lazy('postman_inbox'))),

    url('', include('hosting.urls')),
    url('', include('pages.urls')),
)
