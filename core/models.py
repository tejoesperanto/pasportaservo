import re
import warnings
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.models import TimeStampedModel
from solo.models import SingletonModel

from hosting.fields import RangeIntegerField

from .managers import PoliciesManager


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
        help_text=_("Salt used for encoded unique links. Change it to invalidate all links."))

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
        help_text=_("Delay (in days/hours) after which an object is no longer considered as confirmed."))

    google_analytics_key = models.CharField(
        max_length=13, default='UA-99737795-1', blank=True)

    opencage_api_key = models.CharField(
        max_length=32, default='a27f7e361bdfe11881a987a6e86fb5fd', blank=True)

    # https://openmaptiles.com/hosting/
    openmaptiles_api_key = models.CharField(
        max_length=32, default='iQbjILhp2gs0dgNfTlIV', blank=True)

    def __str__(self):  # pragma: no cover
        return str(_("Site Configuration"))

    class Meta:
        verbose_name = _("Site Configuration")


class Policy(FlatPage):
    EFFECTIVE_DATE_PATTERN = r'^{#\s+([0-9-]+)\s+'
    EFFECTIVE_DATE_FORMAT = '%Y-%m-%d'

    objects = PoliciesManager()

    class Meta:
        proxy = True

    @cached_property
    def effective_date(self):
        return self.get_effective_date_for_policy(self.content)

    @classmethod
    def get_effective_date_for_policy(cls, policy_content):
        try:
            date = re.match(cls.EFFECTIVE_DATE_PATTERN, policy_content).group(1)
            return datetime.strptime(date, cls.EFFECTIVE_DATE_FORMAT).date()
        except AttributeError:
            warnings.warn("Policy does not indicate a date it takes effect on!")
            return None
        except ValueError as err:
            warnings.warn("Policy effective date '{}' is invalid; {}".format(date, err))
            return None


class Agreement(TimeStampedModel):
    user = models.ForeignKey(
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
        return str(_("User {user} agreed to '{policy}' on {date:%Y-%m-%d}")).format(
            user=self.user,
            policy=self.policy_version,
            date=self.created
        )


class UserBrowser(models.Model):
    user = models.ForeignKey(
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
        return (f'{self.user.username}: '
                f'{self.browser_name or "?"} {self.browser_version} '
                f'{_("at")} {self.os_name or "?"} {self.os_version}')

    def __repr__(self):
        return ((f"<User: {self.user.username}"
                 f" · Browser: {self.browser_name} {self.browser_version}"
                 f" · OS: {self.os_name} {self.os_version}")
                + (f" · Device: {self.device_type}" if self.device_type else "")
                + ">")
