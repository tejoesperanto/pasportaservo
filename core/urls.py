from django.contrib.auth.views import (
    PasswordResetCompleteView, PasswordResetDoneView,
)
from django.urls import include, path, re_path
from django.utils.translation import pgettext_lazy
from django.views.generic import TemplateView

from .forms import SystemPasswordResetForm, SystemPasswordResetRequestForm

from .views import (  # isort:skip
    HomeView,
    RegisterView, LoginView, AccountRestoreRequestView, LogoutView,
    PasswordResetView, PasswordResetConfirmView,
    UsernameRemindView, UsernameRemindDoneView,
    AgreementView, AgreementRejectView,
    AccountSettingsView,
    PasswordChangeView, PasswordChangeDoneView, UsernameChangeView,
    EmailUpdateView, EmailVerifyView,
    AccountDeleteView,
    FeedbackView,
    MassMailView, MassMailSentView,
    HtmlFragmentRetrieveView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),

    path(
        pgettext_lazy("URL", 'register/'),
        RegisterView.as_view(), name='register'),
    path(
        pgettext_lazy("URL", 'login/'),
        LoginView.as_view(), name='login'),
    path(
        pgettext_lazy("URL", 'login/reactivate/'),
        AccountRestoreRequestView.as_view(), name='login_restore'),
    path(
        pgettext_lazy("URL", 'logout/'),
        LogoutView.as_view(), name='logout'),

    path(
        pgettext_lazy("URL", 'agreement/'), include([
            path(
                '', AgreementView.as_view(), name='agreement'),
            path(
                pgettext_lazy("URL", 'reject/'),
                AgreementRejectView.as_view(), name='agreement_reject'),
        ])),

    path(
        pgettext_lazy("URL", 'account/settings/'),
        AccountSettingsView.as_view(), name='account_settings'),

    path(
        pgettext_lazy("URL", 'password/'), include([
            path(
                '', PasswordChangeView.as_view(), name='password_change'),
            path(
                pgettext_lazy("URL", 'done/'),
                PasswordChangeDoneView.as_view(), name='password_change_done'),
            path(
                pgettext_lazy("URL", 'reset/'), include([
                    path(
                        '',
                        PasswordResetView.as_view(
                            form_class=SystemPasswordResetRequestForm,
                        ),
                        name='password_reset'),
                    path(
                        pgettext_lazy("URL", 'sent/'),
                        PasswordResetDoneView.as_view(), name='password_reset_done'),
                    re_path(
                        r'^(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/$',
                        view=PasswordResetConfirmView.as_view(
                            form_class=SystemPasswordResetForm,
                        ),
                        name='password_reset_confirm'),
                    path(
                        pgettext_lazy("URL", 'done/'),
                        PasswordResetCompleteView.as_view(), name='password_reset_complete'),
                ])),
        ])),
    path(
        pgettext_lazy("URL", 'username/'), include([
            path(
                '', UsernameChangeView.as_view(), name='username_change'),
            path(
                pgettext_lazy("URL", 'remind/'), include([
                    path(
                        '', UsernameRemindView.as_view(), name='username_remind'),
                    path(
                        pgettext_lazy("URL", 'sent/'),
                        UsernameRemindDoneView.as_view(), name='username_remind_done'),
                ])),
        ])),
    path(
        pgettext_lazy("URL", 'email/'), include([
            path(
                '', EmailUpdateView.as_view(), name='email_update'),
            path(
                pgettext_lazy("URL", 'verify/'),
                EmailVerifyView.as_view(), name='email_verify'),
        ])),

    path(
        pgettext_lazy("URL", 'account/delete/'),
        AccountDeleteView.as_view(), name='account_delete'),

    path(
        pgettext_lazy("URL", 'feedback/'),
        FeedbackView.as_view(), name='user_feedback'),

    path(
        pgettext_lazy("URL", 'admin/'), include([
            path(pgettext_lazy("URL", 'mass-mail/'), include([
                path(
                    '', MassMailView.as_view(), name='mass_mail'),
                path(
                    pgettext_lazy("URL", 'sent/'),
                    MassMailSentView.as_view(), name='mass_mail_sent'),
            ])),
        ])),

    path(
        'fragment/<slug:fragment_id>/',
        HtmlFragmentRetrieveView.as_view(), name='get_fragment'),
    path(
        pgettext_lazy("URL", 'ok'),
        TemplateView.as_view(template_name='200.html')),
]
