from django.conf.urls import include, url
from django.conf import settings
from django.views.generic import RedirectView
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.views import (
    LoginView, LogoutView,
    #PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)

from .views import (
    HomeView,
    RegisterView,
    PasswordChangeView, PasswordChangeDoneView, UsernameChangeView,
    EmailUpdateView, EmailVerifyView,
    MassMailView, MassMailSentView,
)
from .forms import (
    SystemPasswordResetRequestForm, SystemPasswordResetForm
)


urlpatterns = [
    url(r'^$', HomeView.as_view(), name='home'),

    url(_(r'^register/$'), RegisterView.as_view(), name='register'),
    url(_(r'^login/$'),
        view=LoginView.as_view(
            redirect_authenticated_user=True,
            redirect_field_name=settings.REDIRECT_FIELD_NAME,
        ),
        name='login'),
    url(_(r'^logout/$'), view=LogoutView.as_view(next_page='/'), name='logout'),

    url(_(r'^password/'), include([
        url(r'^$', view=PasswordChangeView.as_view(), name='password_change'),
        url(_(r'^done/$'), view=PasswordChangeDoneView.as_view(), name='password_change_done'),
        url(_(r'^reset/'), include([
            url(r'^$',
                view=PasswordResetView.as_view(
                    form_class=SystemPasswordResetRequestForm,
                    html_email_template_name='email/password_reset.html',
                    email_template_name='email/password_reset.txt',
                    subject_template_name='email/password_reset_subject.txt',
                ),
                name='password_reset'),
            url(_(r'^sent/$'), view=PasswordResetDoneView.as_view(), name='password_reset_done'),
            url(r'^(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
                view=PasswordResetConfirmView.as_view(
                    form_class=SystemPasswordResetForm,
                ),
                name='password_reset_confirm'),
            url(_(r'^done/$'), view=PasswordResetCompleteView.as_view(), name='password_reset_complete'),
        ])),
    ])),
    # Backwards-compatibility for older password reset URLs. They become invalid
    # quickly, so can be removed after 31 Dec 2017.
    url(_(r'^reset-password/(?P<uidb64>.+?)/(?P<token>.+?)/$'),
        RedirectView.as_view(pattern_name='password_reset_confirm', permanent=True)),
    url(_(r'^username/$'), UsernameChangeView.as_view(), name='username_change'),
    url(_(r'^email/'), include([
        url(r'^$', EmailUpdateView.as_view(), name='email_update'),
        url(_(r'^verify/$'), EmailVerifyView.as_view(), name='email_verify'),
    ])),

    url(_(r'^admin/'), include([
        url(_(r'^mass-mail/'), include([
            url(r'^$', MassMailView.as_view(), name='mass_mail'),
            url(_(r'^sent/$'), MassMailSentView.as_view(), name='mass_mail_sent'),
        ])),
    ])),
]
