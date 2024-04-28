from collections import namedtuple
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from django.conf import settings
from django.db import models
from django.utils.translation import gettext, gettext_lazy as _

from django_extensions.db.models import TimeStampedModel
from solo.models import SingletonModel

from hosting.fields import RangeIntegerField

from .managers import PoliciesManager

if TYPE_CHECKING:
    from django.db.models import ForeignKey

    from hosting.models import PasportaServoUser


def default_api_keys():  # pragma: no cover
    return dict(
        opencage='a27f7e361bdfe11881a987a6e86fb5fd',
        openmaptiles='iQbjILhp2gs0dgNfTlIV',
    )


class SiteConfiguration(SingletonModel):
    # Legal requirement of GDPR Article 8(1): [...] in relation to the offer
    # of information society services directly to a child, the processing of
    # the personal data of a child shall be lawful where the child is at least
    # 16 years old.
    USER_MIN_AGE = 16

    site_name = models.CharField(
        _("site name"),
        max_length=30, default='Pasporta Servo')

    salt = models.CharField(
        _("encryption salt"),
        max_length=30, default='salo',
        help_text=_("Salt used for encoded unique links. "
                    "Change it to invalidate all links."))

    token_max_age = models.PositiveIntegerField(
        _("unique link lifetime"),
        default=3600 * 24 * 2,
        help_text=_("In seconds: 2 days = 3600 x 24 x 2 = 172800"))

    host_min_age = RangeIntegerField(
        _("minumum age for hosting"),
        min_value=USER_MIN_AGE, default=17)

    meet_min_age = RangeIntegerField(
        _("minumum age for meeting"),
        min_value=USER_MIN_AGE, default=16)

    confirmation_validity_period = models.DurationField(
        _("confirmation validity period"),
        default=timedelta(weeks=42),
        help_text=_("Delay (in days/hours) after which an object is no longer "
                    "considered as confirmed."))

    google_analytics_key = models.CharField(
        max_length=13, default='UA-99737795-1', blank=True)

    mapping_services_api_keys = models.JSONField(
        _("API keys for mapping services"),
        default=default_api_keys)

    class Meta:
        verbose_name = _("Site Configuration")

    def __str__(self):  # pragma: no cover
        return str(_("Site Configuration"))

    @classmethod
    def get_solo(cls):
        return cast(SiteConfiguration, super().get_solo())


class Policy(models.Model):
    version = models.SlugField(
        _("version of policy"),
        max_length=50, unique=True,
        help_text=_("Avoid modifying already-existing versions."))
    effective_date = models.DateField(
        _("in effect from date"),
        unique=True)
    changes_summary = models.TextField(
        _("summary of changes"),
        blank=True)
    content = models.TextField(
        _("content"))
    requires_consent = models.BooleanField(
        _("consent is required"),
        default=True)

    objects = PoliciesManager()

    class Meta:
        verbose_name = _("policy")
        verbose_name_plural = _("policies")
        get_latest_by = 'effective_date'

    def __str__(self):
        if self.requires_consent:
            # xgettext:python-brace-format
            description = gettext("Policy {version} binding from {date:%Y-%m-%d}")
        else:
            # xgettext:python-brace-format
            description = gettext("Policy {version} effective from {date:%Y-%m-%d}")
        return description.format(version=self.version, date=self.effective_date)


class Agreement(TimeStampedModel):
    user: 'ForeignKey[PasportaServoUser]' = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("user"),
        related_name='+', on_delete=models.CASCADE)
    policy_version = models.CharField(
        _("version of policy"),
        max_length=50)
    withdrawn = models.DateTimeField(
        _("withdrawn on"),
        default=None, blank=True, null=True)

    class Meta:
        verbose_name = _("agreement")
        verbose_name_plural = _("agreements")
        default_permissions = ('delete', )
        unique_together = ('user', 'policy_version', 'withdrawn')

    def __str__(self):
        # xgettext:python-brace-format
        return gettext("User {user} agreed to '{policy}' on {date:%Y-%m-%d}").format(
            user=self.user,
            policy=self.policy_version,
            date=self.created,
        )


class UserBrowser(models.Model):
    user: 'ForeignKey[PasportaServoUser | None]' = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("user"),
        related_name='+', null=True, on_delete=models.SET_NULL)
    user_agent_string = models.CharField(
        _("user agent string"),
        max_length=250)
    user_agent_hash = models.CharField(
        _("user agent hash"),
        max_length=32)
    geolocation = models.CharField(
        _("location"),
        blank=True,
        max_length=50,
        help_text=_("Region and country code, separated by comma."))
    added_on = models.DateTimeField(
        _("created"),
        auto_now_add=True)
    os_name = models.CharField(
        _("operating system"),
        blank=True,
        max_length=30)
    os_version = models.CharField(
        _("operating system version"),
        blank=True,
        max_length=15)
    browser_name = models.CharField(
        _("browser"),
        blank=True,
        max_length=30)
    browser_version = models.CharField(
        _("browser version"),
        blank=True,
        max_length=15)
    device_type = models.CharField(
        _("type of device"),
        blank=True,
        max_length=30)

    class Meta:
        verbose_name = _("user browser")
        verbose_name_plural = _("user browsers")

    def __str__(self):
        return (f'{self.user.username if self.user else _("user")}: '
                f'{self.browser_name or "?"} {self.browser_version} '
                f'{_("at")} {self.os_name or "?"} {self.os_version}')

    def __repr__(self):
        return ((f"<User: {self.user.username if self.user else '[DELETED]'}"
                 f" · Browser: {self.browser_name} {self.browser_version}"
                 f" · OS: {self.os_name} {self.os_version}")
                + (f" · Device: {self.device_type}" if self.device_type else "")
                + ">")


# TODO: Fetch from feature flags.
FeedbackType = namedtuple('FeedbackType', 'key, name, esperanto_name, foreign_id, url')
FEEDBACK_TYPES = {
    'adv_search': FeedbackType('adv_search', 'advanced search', 'nuancita serĉo', 'D_kwDOAtBdzs4APmhx', ''),
}
