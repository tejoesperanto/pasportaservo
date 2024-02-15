from typing import Protocol, TypedDict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    LoginRequiredMixin as AuthenticatedUserRequiredMixin,
)
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db.models import Q
from django.db.models.functions import Lower
from django.urls import reverse_lazy
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View

from hosting.models import Profile
from hosting.utils import value_without_invalid_marker
from hosting.validators import AccountAttributesSimilarityValidator

from .auth import auth_log
from .utils import is_password_compromised, sanitize_next

User = get_user_model()


class LoginRequiredMixin(AuthenticatedUserRequiredMixin):
    """
    An own view mixin enabling the usage of a custom URL parameter name
    for the redirection after successful authentication. Needed due to
    arbitrary limitations on the parameter name customization by Django.
    """
    redirect_field_name = settings.REDIRECT_FIELD_NAME


class UserModifyMixin(object):
    def get_success_url(self, *args, **kwargs):
        redirect_to = sanitize_next(self.request)
        if redirect_to:
            return redirect_to

        try:
            if hasattr(self.object, self.object._meta.get_field('profile').get_cache_name()):
                profile = self.object.profile
            else:
                profile = Profile.get_basic_data(user=self.object)
            return profile.get_edit_url()
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')


class FlatpageAsTemplateMixin:
    class DictWithContent(TypedDict):
        content: str

    class HasContent(Protocol):
        content: str

    def render_flat_page(self, page: DictWithContent | HasContent) -> str:
        ...


def flatpages_as_templates(cls: type[View]):
    """
    View decorator:
    Facilitates rendering flat pages as Django templates, including usage of
    tags and the view's context. Performs some magic to capture the specific
    view's custom context and provides a helper function `render_flat_page`.
    This helper function shouldn't be called from within get_context_data()!
    """
    context_func_name = 'get_context_data'
    context_func = getattr(cls, context_func_name, None)
    if context_func:
        def _get_context_data_superfunc(self, **kwargs):
            context = context_func(self, **kwargs)
            self._flat_page_context = context
            return context
        setattr(cls, context_func_name, _get_context_data_superfunc)

    def render_flat_page(
            self,
            page: FlatpageAsTemplateMixin.DictWithContent | FlatpageAsTemplateMixin.HasContent,
    ):
        if not page:
            return ''
        from django.template import engines
        content = page['content'] if isinstance(page, dict) else page.content
        template = engines.all()[0].from_string(content)
        return template.render(
            getattr(self, '_flat_page_context', render_flat_page._view_context),
            self.request)
    setattr(cls, 'render_flat_page',  render_flat_page)
    getattr(cls, 'render_flat_page')._view_context = {}

    return cls


class UsernameFormMixin(object):
    """
    A form mixin that performs a case-insensitive uniqueness validation of the
    provided username value on form submit.
    """
    username_error_messages = {
        # We do not want to disclose the exact usernames in the system through
        # the error messages, and thus facilitate user enumeration attacks...
        'unique': _("A user with a similar username already exists."),
        # Clearly spell out to the potential new users what a valid username is.
        'invalid': lazy(mark_safe, str)(_(
            "Enter a username conforming to these rules: "
            " This value may contain only letters, numbers, and the symbols"
            " <kbd>@</kbd> <kbd>.</kbd> <kbd>+</kbd> <kbd>-</kbd> <kbd>_</kbd>."
            " Spaces are not allowed."
        )),
        # Indicate what are the limitations in terms of number of characters.
        'max_length': _(
            "Ensure that this value has at most %(limit_value)d characters "
            "(it has now %(show_value)d)."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Stores the value before the change.
        self.previous_uname = self.instance.username

    def clean_username(self):
        """
        Ensure that the username provided is unique (in a case-insensitive manner).
        This check replaces the Django's built-in uniqueness verification.
        """
        username = self.cleaned_data['username']
        if username == self.previous_uname:
            return username
        threshold = 1 if username.lower() != self.previous_uname.lower() else 2
        if User.objects.filter(username__iexact=username).count() >= threshold:
            raise ValidationError(self._meta.error_messages['username']['unique'])
        return username


class SystemEmailFormMixin(object):
    """
    A form mixin that performs a case-insensitive uniqueness validation of the
    provided email address value on form submit. Both valid and invalid existing
    emails in the database are taken into account.
    """
    email_error_messages = {
        'max_length': _(
            "Ensure that this value has at most %(limit_value)d characters "
            "(it has now %(show_value)d)."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Stores the value before the change.
        self.previous_email = value_without_invalid_marker(self.instance.email)

    def clean_email(self):
        """
        Ensure that the email address provided is unique (in a case-insensitive manner).
        """
        email_value = self.cleaned_data['email']
        if not email_value:
            raise ValidationError(_("Enter a valid email address."))
        if email_value.startswith(settings.INVALID_PREFIX):
            raise ValidationError(format_lazy(
                _("Email address cannot start with {PREFIX} (in all-capital letters)."),
                PREFIX=settings.INVALID_PREFIX
            ))
        invalid_email = '{}{}'.format(settings.INVALID_PREFIX, email_value)
        emails_lookup = Q(email_lc=email_value.lower()) | Q(email_lc=invalid_email.lower())
        if email_value and email_value.lower() != self.previous_email.lower() \
                and User.objects.annotate(email_lc=Lower('email')).filter(emails_lookup).exists():
            raise ValidationError(_("User address already in use."))
        return email_value


class PasswordFormMixin(object):
    """
    A form mixin adding a functionality of validating the submitted password
    value against several criteria:
    -  Similarity to other attributes of the account / profile;
    -  Verification (anonymously) whether the value has not been compromised,
       via the HIBP's Pwned Passwords service.

    While Django comes with a built in password validation mechanism (AUTH_PASSWORD_VALIDATORS),
    it is too rigid, from presentation: help texts, hardcoded error messages;
    to association: which form field is validated; to function: inability to
    customise behaviour without rewriting the validation logic.
    """

    def analyze_password(self, password_field_value):
        insecure, howmuch = is_password_compromised(password_field_value)

        if insecure and howmuch > 99:
            self.add_error(NON_FIELD_ERRORS, ValidationError(_(
                "The password selected by you is too insecure. "
                "Such combination of characters is very well-known to cyber-criminals."),
                code='compromised_password'))
            self.add_error(self.analyze_password_field, _("Choose a less easily guessable password."))
        elif insecure and howmuch > 1:
            self.add_error(NON_FIELD_ERRORS, ValidationError(_(
                "The password selected by you is not very secure. "
                "Such combination of characters is known to cyber-criminals."),
                code='compromised_password'))
            self.add_error(self.analyze_password_field, _("Choose a less easily guessable password."))

        if insecure:
            auth_log.warning(
                "Password with HIBP count {:d} selected in {}.".format(howmuch, self.__class__.__name__),
                extra={'request': self.view_request} if hasattr(self, 'view_request') else None,
            )

    def clean(self):
        cleaned_data = super().clean()
        if self.analyze_password_field in cleaned_data:
            cleaned_password = cleaned_data[self.analyze_password_field]
            try:
                user = getattr(self, 'user', getattr(self, 'proxy_user', None))
                AccountAttributesSimilarityValidator()(cleaned_password, user)
            except ValidationError as e:
                self.add_error(self.analyze_password_field, e)
            else:
                self.analyze_password(cleaned_password)
        return cleaned_data
