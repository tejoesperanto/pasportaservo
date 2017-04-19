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
    username_change,
    email_update, staff_update_email, email_verify,
    mark_email_invalid, mark_email_valid,
    mass_mail, mass_mail_sent,
)
from .forms import (
    SystemPasswordResetRequestForm, SystemPasswordResetForm
)


urlpatterns = [
    url(r'^$', home, name='home'),

    url(_(r'^register/$'), register, name='register'),
    url(_(r'^login/$'), view=login, name='login'),
    url(_(r'^logout/$'), view=logout, kwargs={'next_page': '/'}, name='logout'),

    url(_(r'^password/$'), view=password_change, name='password_change'),
    url(_(r'^password/done/$'), view=password_change_done, name='password_change_done'),
    url(_(r'^password/reset/$'), view=password_reset, name='password_reset',
        kwargs={'password_reset_form': SystemPasswordResetRequestForm,
                'html_email_template_name': 'email/password_reset.html',
                'email_template_name': 'email/password_reset.txt',
                'subject_template_name': 'email/password_reset_subject.txt'}),
    url(_(r'^password/reset/done/$'), view=password_reset_done, name='password_reset_done'),
    url(_(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'),
        view=password_reset_confirm, name='password_reset_confirm',
        kwargs={'set_password_form': SystemPasswordResetForm}),
    url(_(r'^reset/done/$'), view=password_reset_complete, name='password_reset_complete'),

    url(_(r'^username/$'), username_change, name='username_change'),
    url(_(r'^email/$'), email_update, name='email_update'),
    url(_(r'^profile/(?P<pk>\d+)/staff/email/update/$'), staff_update_email, name='staff_update_email'),
    url(_(r'^profile/(?P<pk>\d+)/staff/email/mark-invalid/$'), mark_email_invalid, name='staff_mark_email_invalid'),
    url(_(r'^profile/(?P<pk>\d+)/staff/email/mark-valid/$'), mark_email_valid, name='staff_mark_email_valid'),
    url(_(r'^email/verify/$'), email_verify, name='email_verify'),

    url(_(r'^admin/mass-mail/$'), mass_mail, name='mass_mail'),
    url(_(r'^admin/mass-mail/sent/$'), mass_mail_sent, name='mass_mail_sent'),
]
