from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.views import (
    login, logout,
    password_change, password_change_done,
    password_reset, password_reset_done,
    password_reset_confirm, password_reset_complete,
)

from .views import (
    home,
    register,
    mass_mail, mass_mail_sent,
)


urlpatterns = [
    url(r'^$', home, name='home'),

    url(_(r'^register/$'), register, name='register'),
    url(_(r'^login/$'), view=login, name='login'),
    url(_(r'^logout/$'), view=logout, kwargs={'next_page': '/'}, name='logout'),

    url(_(r'^password/$'), view=password_change, name='password_change'),
    url(_(r'^password/done/$'), view=password_change_done, name='password_change_done'),
    url(_(r'^password/reset/$'), view=password_reset, name='password_reset',
        kwargs={'html_email_template_name': 'registration/password_reset_email_html.html'}),
    url(_(r'^password/reset/done/$'), view=password_reset_done, name='password_reset_done'),
    url(_(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'),
        view=password_reset_confirm, name='password_reset_confirm'),
    url(_(r'^reset/done/$'), view=password_reset_complete, name='password_reset_complete'),

    url(_(r'^mass_mail/$'), mass_mail, name='mass_mail'),
    url(_(r'^mass_mail_sent/$'), mass_mail_sent, name='mass_mail_sent'),
]
